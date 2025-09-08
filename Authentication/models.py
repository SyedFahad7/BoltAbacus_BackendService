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


class PersonalGoal(models.Model):
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    TYPE_CHOICES = [
        ('personal', 'Personal'),
        ('practice', 'Practice'),
        ('streak', 'Streak'),
        ('level', 'Level'),
        ('pvp', 'PVP'),
    ]
    
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='personal_goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    goal_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='personal')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.firstName} {self.user.lastName} - {self.title}"


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
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0, db_index=True)
    max_streak = models.IntegerField(default=0, db_index=True)
    last_activity_date = models.DateField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user',)
        db_table = 'Authentication_userstreak'
        indexes = [
            models.Index(fields=['user', 'last_activity_date']),
            models.Index(fields=['current_streak']),
            models.Index(fields=['max_streak']),
        ]

    def __str__(self):
        return f"Streak for {self.user.firstName} {self.user.lastName}: {self.current_streak} days"

    def update_streak(self, activity_date=None):
        """Update streak based on activity date with improved logic"""
        if activity_date is None:
            activity_date = date.today()
        
        # Handle timezone-aware dates
        if hasattr(activity_date, 'date'):
            activity_date = activity_date.date()
        
        if self.last_activity_date is None:
            # First time activity
            self.current_streak = 1
            self.max_streak = 1
            self.last_activity_date = activity_date
        else:
            # Check if it's a consecutive day
            days_diff = (activity_date - self.last_activity_date).days
            
            if days_diff == 1:
                # Consecutive day
                self.current_streak += 1
                self.max_streak = max(self.max_streak, self.current_streak)
            elif days_diff == 0:
                # Same day, no change needed
                return self.current_streak
            elif days_diff < 0:
                # Future date (shouldn't happen in normal usage)
                return self.current_streak
            else:
                # Streak broken (more than 1 day gap), start new streak
                self.current_streak = 1
            
            self.last_activity_date = activity_date
        
        self.save(update_fields=['current_streak', 'max_streak', 'last_activity_date', 'updated_at'])
        return self.current_streak

    def reset_streak(self):
        """Reset the current streak to 0"""
        self.current_streak = 0
        self.last_activity_date = None
        self.save(update_fields=['current_streak', 'last_activity_date', 'updated_at'])
        return self.current_streak

    @classmethod
    def get_or_create_streak(cls, user):
        """Get or create streak for user with proper error handling"""
        try:
            streak, created = cls.objects.get_or_create(user=user)
            return streak, created
        except Exception as e:
            # Log the error for debugging
            print(f"Error getting/creating streak for user {user.userId}: {e}")
            # Try to get existing streak
            try:
                streak = cls.objects.filter(user=user).first()
                if streak:
                    return streak, False
                else:
                    # Create new streak if none exists
                    streak = cls.objects.create(user=user)
                    return streak, True
            except Exception as e2:
                print(f"Critical error creating streak for user {user.userId}: {e2}")
                raise


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


# Daily Progress Tracking Model
class DailyProgress(models.Model):
    user = models.ForeignKey(UserDetails, to_field='userId', on_delete=models.CASCADE, related_name='daily_progress')
    date = models.DateField(db_index=True)
    
    # Daily aggregated metrics
    total_accuracy = models.FloatField(default=0.0)  # Average accuracy for the day
    total_speed = models.FloatField(default=0.0)     # Average problems per minute
    total_activities = models.IntegerField(default=0)  # Number of activities completed
    total_time_spent = models.IntegerField(default=0)  # Total time in seconds
    
    # Activity breakdown
    classwork_completed = models.IntegerField(default=0)
    homework_completed = models.IntegerField(default=0)
    tests_completed = models.IntegerField(default=0)
    practice_sessions = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'date']
        db_table = 'Authentication_dailyprogress'
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.user.firstName} - {self.date}: {self.total_accuracy}% accuracy, {self.total_speed} problems/min"

    @classmethod
    def update_daily_progress(cls, user, accuracy, speed, time_spent, activity_type='classwork'):
        """Update or create daily progress record"""
        today = date.today()
        
        # Get or create today's record
        daily_progress, created = cls.objects.get_or_create(
            user=user,
            date=today,
            defaults={
                'total_accuracy': accuracy,
                'total_speed': speed,
                'total_activities': 1,
                'total_time_spent': time_spent,
                'classwork_completed': 1 if activity_type == 'classwork' else 0,
                'homework_completed': 1 if activity_type == 'homework' else 0,
                'tests_completed': 1 if activity_type == 'test' else 0,
                'practice_sessions': 1 if activity_type == 'practice' else 0,
            }
        )
        
        if not created:
            # Update existing record with weighted averages
            old_activities = daily_progress.total_activities
            new_activities = old_activities + 1
            
            # Calculate weighted averages
            daily_progress.total_accuracy = (
                (daily_progress.total_accuracy * old_activities + accuracy) / new_activities
            )
            daily_progress.total_speed = (
                (daily_progress.total_speed * old_activities + speed) / new_activities
            )
            
            # Update counters
            daily_progress.total_activities = new_activities
            daily_progress.total_time_spent += time_spent
            
            # Update activity type counters
            if activity_type == 'classwork':
                daily_progress.classwork_completed += 1
            elif activity_type == 'homework':
                daily_progress.homework_completed += 1
            elif activity_type == 'test':
                daily_progress.tests_completed += 1
            elif activity_type == 'practice':
                daily_progress.practice_sessions += 1
            
            daily_progress.save()
        
        return daily_progress

    @classmethod
    def get_weekly_trend(cls, user, days=7):
        """Get weekly trend data for charts"""
        from datetime import timedelta
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days-1)
        
        # Get all records for the week
        weekly_data = cls.objects.filter(
            user=user,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Create a complete week array
        trend_data = []
        labels = []
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_name = current_date.strftime('%a')  # Mon, Tue, etc.
            
            # Find data for this date
            day_data = weekly_data.filter(date=current_date).first()
            
            if day_data:
                trend_data.append(round(day_data.total_accuracy, 1))
            else:
                trend_data.append(0)
            
            # Create labels (show day names for better UX)
            if i == 0:
                labels.append(f"{days-1}d ago")
            elif i == days - 1:
                labels.append("Today")
            else:
                labels.append(day_name)
        
        return {
            'accuracy': trend_data,
            'speed': [round(day_data.total_speed, 1) if day_data else 0 for day_data in weekly_data],
            'labels': labels,
            'current_accuracy': trend_data[-1] if trend_data else 0,
            'current_speed': weekly_data.last().total_speed if weekly_data.exists() else 0,
            'weekly_progress': round(trend_data[-1] - trend_data[0], 1) if len(trend_data) > 1 else 0
        }