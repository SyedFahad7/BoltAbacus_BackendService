import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import PVPRoom, PVPRoomPlayer, PVPGameSession, PVPPlayerAnswer, QuizQuestions
import random


class PVPConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'pvp_{self.room_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        user_id = text_data_json.get('user_id')

        if message_type == 'join_room':
            await self.handle_join_room(user_id)
        elif message_type == 'player_ready':
            await self.handle_player_ready(user_id)
        elif message_type == 'submit_answer':
            await self.handle_submit_answer(user_id, text_data_json)
        elif message_type == 'start_game':
            await self.handle_start_game(user_id)

    async def handle_join_room(self, user_id):
        """Handle when a player joins the room"""
        room = await self.get_room()
        if not room:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Room not found'
            }))
            return

        # Check if room is full
        if room.current_players >= room.max_players:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Room is full'
            }))
            return

        # Add player to room
        player = await self.add_player_to_room(user_id, room)
        if player:
            # Update room player count
            await self.update_room_player_count(room)
            
            # Send room update to all players
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'room_update',
                    'room_data': await self.get_room_data(room)
                }
            )

    async def handle_player_ready(self, user_id):
        """Handle when a player marks themselves as ready"""
        player = await self.set_player_ready(user_id)
        if player:
            room = await self.get_room()
            
            # Check if all players are ready
            all_ready = await self.check_all_players_ready(room)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'player_ready_update',
                    'user_id': user_id,
                    'all_ready': all_ready,
                    'room_data': await self.get_room_data(room)
                }
            )

    async def handle_start_game(self, user_id):
        """Handle game start request"""
        room = await self.get_room()
        if room.creator.userId != user_id:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Only room creator can start the game'
            }))
            return

        # Check if all players are ready
        all_ready = await self.check_all_players_ready(room)
        if not all_ready:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'All players must be ready to start'
            }))
            return

        # Start the game
        await self.start_game(room)
        
        # Send game start to all players
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_started',
                'room_data': await self.get_room_data(room)
            }
        )

    async def handle_submit_answer(self, user_id, data):
        """Handle when a player submits an answer"""
        answer = data.get('answer')
        question_id = data.get('question_id')
        time_taken = data.get('time_taken', 0)

        # Save the answer
        await self.save_player_answer(user_id, question_id, answer, time_taken)
        
        # Check if all players have answered
        all_answered = await self.check_all_players_answered()
        
        if all_answered:
            # Move to next question or end game
            await self.handle_question_completion()

    async def room_update(self, event):
        """Send room update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'room_update',
            'room_data': event['room_data']
        }))

    async def player_ready_update(self, event):
        """Send player ready update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'player_ready_update',
            'user_id': event['user_id'],
            'all_ready': event['all_ready'],
            'room_data': event['room_data']
        }))

    async def game_started(self, event):
        """Send game started message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'game_started',
            'room_data': event['room_data']
        }))

    async def question_update(self, event):
        """Send question update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'question_update',
            'question_data': event['question_data']
        }))

    async def game_result(self, event):
        """Send game result to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'game_result',
            'result_data': event['result_data']
        }))

    # Database operations
    @database_sync_to_async
    def get_room(self):
        try:
            return PVPRoom.objects.get(room_id=self.room_id)
        except PVPRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def add_player_to_room(self, user_id, room):
        from .models import UserDetails
        try:
            user = UserDetails.objects.get(userId=user_id)
            player, created = PVPRoomPlayer.objects.get_or_create(
                room=room,
                player=user,
                defaults={'status': 'joined'}
            )
            return player
        except UserDetails.DoesNotExist:
            return None

    @database_sync_to_async
    def update_room_player_count(self, room):
        room.current_players = room.players.count()
        room.save()

    @database_sync_to_async
    def get_room_data(self, room):
        players_data = []
        for player in room.players.all():
            players_data.append({
                'user_id': player.player.userId,
                'name': f"{player.player.firstName} {player.player.lastName}",
                'status': player.status,
                'is_ready': player.is_ready,
                'score': player.score
            })
        
        return {
            'room_id': room.room_id,
            'status': room.status,
            'max_players': room.max_players,
            'current_players': room.current_players,
            'number_of_questions': room.number_of_questions,
            'time_per_question': room.time_per_question,
            'players': players_data
        }

    @database_sync_to_async
    def set_player_ready(self, user_id):
        try:
            player = PVPRoomPlayer.objects.get(
                room__room_id=self.room_id,
                player__userId=user_id
            )
            player.is_ready = True
            player.status = 'ready'
            player.ready_at = timezone.now()
            player.save()
            return player
        except PVPRoomPlayer.DoesNotExist:
            return None

    @database_sync_to_async
    def check_all_players_ready(self, room):
        total_players = room.players.count()
        ready_players = room.players.filter(is_ready=True).count()
        return total_players > 0 and total_players == ready_players

    @database_sync_to_async
    def start_game(self, room):
        room.status = 'active'
        room.started_at = timezone.now()
        room.save()

        # Create game session
        game_session, created = PVPGameSession.objects.get_or_create(
            room=room,
            defaults={'is_active': True}
        )
        
        # Get first question
        questions = QuizQuestions.objects.filter(
            quiz__levelId=room.level_id,
            quiz__classId=room.class_id,
            quiz__topicId=room.topic_id
        ).order_by('?')[:room.number_of_questions]
        
        if questions.exists():
            game_session.current_question = questions[0]
            game_session.save()

    @database_sync_to_async
    def save_player_answer(self, user_id, question_id, answer, time_taken):
        from .models import UserDetails
        try:
            user = UserDetails.objects.get(userId=user_id)
            question = QuizQuestions.objects.get(questionId=question_id)
            room = PVPRoom.objects.get(room_id=self.room_id)
            game_session = PVPGameSession.objects.get(room=room)
            
            is_correct = str(question.correctAnswer).strip() == str(answer).strip()
            
            player_answer, created = PVPPlayerAnswer.objects.get_or_create(
                game_session=game_session,
                player=user,
                question=question,
                defaults={
                    'answer': answer,
                    'is_correct': is_correct,
                    'time_taken': time_taken
                }
            )
            
            # Update player score
            player = PVPRoomPlayer.objects.get(room=room, player=user)
            if is_correct:
                player.score += 10
                player.correct_answers += 1
            player.total_time += time_taken
            player.save()
            
            return player_answer
        except Exception as e:
            print(f"Error saving answer: {e}")
            return None

    @database_sync_to_async
    def check_all_players_answered(self):
        room = PVPRoom.objects.get(room_id=self.room_id)
        game_session = PVPGameSession.objects.get(room=room)
        current_question = game_session.current_question
        
        total_players = room.players.count()
        answered_players = PVPPlayerAnswer.objects.filter(
            game_session=game_session,
            question=current_question
        ).count()
        
        return total_players > 0 and total_players == answered_players

    @database_sync_to_async
    def handle_question_completion(self):
        room = PVPRoom.objects.get(room_id=self.room_id)
        game_session = PVPGameSession.objects.get(room=room)
        
        # Move to next question or end game
        current_index = game_session.current_question_index
        if current_index < room.number_of_questions - 1:
            # Move to next question
            game_session.current_question_index += 1
            questions = QuizQuestions.objects.filter(
                quiz__levelId=room.level_id,
                quiz__classId=room.class_id,
                quiz__topicId=room.topic_id
            ).order_by('?')[current_index + 1:current_index + 2]
            
            if questions.exists():
                game_session.current_question = questions[0]
                game_session.save()
        else:
            # End game
            await self.end_game(room)

    @database_sync_to_async
    def end_game(self, room):
        room.status = 'finished'
        room.finished_at = timezone.now()
        room.save()
        
        # Determine winner
        players = room.players.all().order_by('-score', 'total_time')
        winner = players.first() if players.exists() else None
        
        # Award experience points
        if winner:
            await self.award_experience(winner.player, 50)  # 50 XP for winning
        
        # Create game result
        from .models import PVPGameResult
        PVPGameResult.objects.create(
            room=room,
            winner=winner.player if winner else None,
            winner_score=winner.score if winner else 0,
            winner_correct_answers=winner.correct_answers if winner else 0,
            winner_time=winner.total_time if winner else 0,
            experience_awarded=50 if winner else 0
        )

    @database_sync_to_async
    def award_experience(self, user, xp_amount):
        from .models import UserExperience
        user_exp, created = UserExperience.objects.get_or_create(
            user=user,
            defaults={'experience_points': 0, 'level': 1}
        )
        user_exp.experience_points += xp_amount
        
        # Calculate level (every 100 XP = 1 level)
        new_level = (user_exp.experience_points // 100) + 1
        user_exp.level = new_level
        user_exp.save()
        
        return user_exp
