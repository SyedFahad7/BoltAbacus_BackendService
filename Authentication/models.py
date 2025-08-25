from django.db import models
from datetime import date


# from django.contrib.auth.models import AbstractBaseUser


class OrganizationTag(models.Model):
    tagId = models.AutoField(primary_key=True)
    organizationName = models.CharField(max_length=255)
    tagName = models.CharField(max_length=255, default="BoltAbacus", unique=True)
    isIndividualTeacher = models.BooleanField(default=False)
    numberOfTeachers = models.IntegerField(default=0)
    numberOfStudents = models.IntegerField(default=0)
    expirationDate = models.DateField(default=date.today)
    totalNumberOfStudents = models.IntegerField(default=0)
    maxLevel = models.IntegerField(default=1)
    maxClass = models.IntegerField(default=1)


class UserDetails(models.Model):
    userId = models.AutoField(primary_key=True)
    firstName = models.CharField(max_length=50)
    lastName = models.CharField(max_length=50)
    phoneNumber = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50)
    encryptedPassword = models.CharField(max_length=255)
    created_date = models.DateField()
    blocked = models.BooleanField()
    blockedTimestamp = models.DateField(default=date.today)
    tag = models.ForeignKey(OrganizationTag, to_field="tagId", null=True, on_delete=models.CASCADE)


class TopicDetails(models.Model):
    levelId = models.IntegerField()
    classId = models.IntegerField()
    topicId = models.IntegerField()


class Curriculum(models.Model):
    quizId = models.AutoField(primary_key=True)
    levelId = models.IntegerField()
    classId = models.IntegerField()
    topicId = models.IntegerField()
    quizType = models.CharField(max_length=50)
    quizName = models.CharField(max_length=50)


class QuizQuestions(models.Model):
    questionId = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Curriculum, to_field='quizId', null=True, on_delete=models.CASCADE)
    question = models.CharField(max_length=1000)
    correctAnswer = models.CharField(max_length=255)


class Progress(models.Model):
    quiz = models.ForeignKey(Curriculum, to_field='quizId', null=True, on_delete=models.CASCADE)
    user = models.ForeignKey(UserDetails, to_field='userId', null=True, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    time = models.IntegerField(default=0)
    quizPass = models.BooleanField(default=False)
    percentage = models.FloatField(default=0)


class Batch(models.Model):
    batchId = models.AutoField(primary_key=True)
    timeDay = models.CharField(max_length=50)
    timeSchedule = models.CharField(max_length=100)
    numberOfStudents = models.IntegerField()
    active = models.BooleanField()
    batchName = models.CharField(max_length=255)
    latestLevelId = models.IntegerField()
    latestClassId = models.IntegerField()
    latestLink = models.CharField(max_length=500)
    tag = models.ForeignKey(OrganizationTag, to_field="tagId", null=True, on_delete=models.CASCADE)


class Student(models.Model):
    user = models.OneToOneField(UserDetails, to_field='userId', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, to_field='batchId', on_delete=models.DO_NOTHING)
    latestLevelId = models.IntegerField(default=1)
    latestClassId = models.IntegerField(default=1)


class Teacher(models.Model):
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE)
    batchId = models.IntegerField()


class PracticeQuestions(models.Model):
    practiceQuestionId = models.AutoField(primary_key=True)
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE)
    practiceType = models.CharField(max_length=20)
    operation = models.CharField(max_length=50)
    numberOfDigits = models.IntegerField(default=1)
    numberOfQuestions = models.IntegerField(default=0)
    numberOfRows = models.IntegerField(default=1)
    zigZag = models.BooleanField(default=False)
    includeSubtraction = models.BooleanField(default=False)
    persistNumberOfDigits = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    totalTime = models.FloatField(default=0)
    averageTime = models.FloatField(default=0)


# PVP and Experience Models
class UserExperience(models.Model):
    user = models.OneToOneField(UserDetails, to_field='userId', on_delete=models.CASCADE)
    experience_points = models.IntegerField(default=0)
    level = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.firstName} {self.user.lastName} - Level {self.level} ({self.experience_points} XP)"


class PVPRoom(models.Model):
    ROOM_STATUS_CHOICES = [
        ('waiting', 'Waiting for Players'),
        ('ready', 'Players Ready'),
        ('starting', 'Game Starting'),
        ('active', 'Game Active'),
        ('finished', 'Game Finished'),
        ('cancelled', 'Cancelled'),
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]
    
    room_id = models.CharField(max_length=10, unique=True, primary_key=True)
    creator = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='created_rooms')
    max_players = models.IntegerField(default=2)
    current_players = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=ROOM_STATUS_CHOICES, default='waiting')
    number_of_questions = models.IntegerField(default=10)
    time_per_question = models.IntegerField(default=30)  # in seconds
    difficulty_level = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    level_id = models.IntegerField(default=1)
    class_id = models.IntegerField(default=1)
    topic_id = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Room {self.room_id} - {self.creator.firstName} ({self.current_players}/{self.max_players})"


class PVPRoomPlayer(models.Model):
    PLAYER_STATUS_CHOICES = [
        ('joined', 'Joined'),
        ('ready', 'Ready'),
        ('playing', 'Playing'),
        ('finished', 'Finished'),
        ('left', 'Left'),
    ]
    
    room = models.ForeignKey(PVPRoom, to_field='room_id', on_delete=models.CASCADE, related_name='players')
    player = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='pvp_rooms')
    status = models.CharField(max_length=20, choices=PLAYER_STATUS_CHOICES, default='joined')
    is_ready = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    correct_answers = models.IntegerField(default=0)
    total_time = models.FloatField(default=0)
    joined_at = models.DateTimeField(auto_now_add=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['room', 'player']

    def __str__(self):
        return f"{self.player.firstName} in Room {self.room.room_id}"


class PVPGameSession(models.Model):
    room = models.OneToOneField(PVPRoom, to_field='room_id', on_delete=models.CASCADE, related_name='game_session')
    current_question_index = models.IntegerField(default=0)
    current_question = models.ForeignKey(QuizQuestions, on_delete=models.SET_NULL, null=True, blank=True)
    question_start_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Game Session for Room {self.room.room_id}"


class PVPPlayerAnswer(models.Model):
    game_session = models.ForeignKey(PVPGameSession, on_delete=models.CASCADE, related_name='player_answers')
    player = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE)
    question = models.ForeignKey(QuizQuestions, on_delete=models.CASCADE)
    answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    time_taken = models.FloatField(default=0)  # in seconds
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['game_session', 'player', 'question']

    def __str__(self):
        return f"{self.player.firstName} - Q{self.question.questionId} - {'Correct' if self.is_correct else 'Incorrect'}"


class PVPGameResult(models.Model):
    room = models.OneToOneField(PVPRoom, to_field='room_id', on_delete=models.CASCADE, related_name='game_result')
    winner = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='pvp_wins', null=True, blank=True)
    winner_score = models.IntegerField(default=0)
    winner_correct_answers = models.IntegerField(default=0)
    winner_time = models.FloatField(default=0)
    experience_awarded = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for Room {self.room.room_id} - Winner: {self.winner.firstName if self.winner else 'None'}"


# Additional models for future features
class UserStreak(models.Model):
    user = models.OneToOneField(UserDetails, to_field='userId', on_delete=models.CASCADE)
    current_streak = models.IntegerField(default=0)
    max_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.firstName} - {self.current_streak} day streak"


class UserCoins(models.Model):
    user = models.OneToOneField(UserDetails, to_field='userId', on_delete=models.CASCADE)
    balance = models.IntegerField(default=0)
    total_earned = models.IntegerField(default=0)
    total_spent = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.firstName} - {self.balance} coins"


class UserAchievement(models.Model):
    ACHIEVEMENT_TYPES = [
        ('first_win', 'First Win'),
        ('streak_3', '3 Day Streak'),
        ('streak_7', '7 Day Streak'),
        ('streak_30', '30 Day Streak'),
        ('pvp_master', 'PVP Master'),
        ('speed_demon', 'Speed Demon'),
        ('perfect_score', 'Perfect Score'),
    ]
    
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='achievements')
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255)

    class Meta:
        unique_together = ['user', 'achievement_type']

    def __str__(self):
        return f"{self.user.firstName} - {self.get_achievement_type_display()}"
