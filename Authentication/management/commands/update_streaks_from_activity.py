from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from Authentication.models import UserStreak, UserDetails, Progress, PVPRoomPlayer


class Command(BaseCommand):
    help = 'Update streaks based on recent user activity (practice sessions, PVP games)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for activity (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_back = options['days']
        cutoff_date = timezone.now() - timedelta(days=days_back)
        
        # Find users who have had activity in the last N days
        active_users = set()
        
        # Check practice sessions
        practice_users = Progress.objects.filter(
            created_at__gte=cutoff_date
        ).values_list('user', flat=True).distinct()
        active_users.update(practice_users)
        
        # Check PVP games
        pvp_users = PVPRoomPlayer.objects.filter(
            finished_at__gte=cutoff_date
        ).values_list('player', flat=True).distinct()
        active_users.update(pvp_users)
        
        self.stdout.write(f'Found {len(active_users)} users with activity in the last {days_back} days.')
        
        updated_count = 0
        for user_id in active_users:
            try:
                user = UserDetails.objects.get(userId=user_id)
                streak, created = UserStreak.get_or_create_streak(user)
                
                # Update streak with today's date
                old_streak = streak.current_streak
                new_streak = streak.update_streak(date.today())
                
                if new_streak != old_streak or created:
                    updated_count += 1
                    if dry_run:
                        self.stdout.write(
                            f'Would update streak for {user.firstName} {user.lastName} '
                            f'(was: {old_streak}, would be: {new_streak})'
                        )
                    else:
                        self.stdout.write(
                            f'Updated streak for {user.firstName} {user.lastName} '
                            f'(was: {old_streak}, now: {new_streak})'
                        )
                        
            except UserDetails.DoesNotExist:
                self.stdout.write(f'User with ID {user_id} not found, skipping.')
                continue
            except Exception as e:
                self.stdout.write(f'Error updating streak for user {user_id}: {e}')
                continue
        
        if dry_run:
            self.stdout.write(f'DRY RUN - Would update {updated_count} streaks.')
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully updated {updated_count} streaks.')
            )
