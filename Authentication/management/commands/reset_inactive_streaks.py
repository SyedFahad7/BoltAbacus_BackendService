from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from Authentication.models import UserStreak, UserDetails


class Command(BaseCommand):
    help = 'Reset streaks for users who have been inactive for more than 1 day'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be reset without actually resetting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Find streaks that haven't been updated in more than 1 day
        inactive_streaks = UserStreak.objects.filter(
            last_activity_date__lt=yesterday
        ).exclude(current_streak=0)
        
        count = inactive_streaks.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No inactive streaks found to reset.')
            )
            return
        
        self.stdout.write(f'Found {count} inactive streaks to reset.')
        
        if dry_run:
            self.stdout.write('DRY RUN - No streaks will be reset.')
            for streak in inactive_streaks:
                self.stdout.write(
                    f'Would reset streak for {streak.user.firstName} {streak.user.lastName} '
                    f'(current: {streak.current_streak}, last activity: {streak.last_activity_date})'
                )
        else:
            reset_count = 0
            for streak in inactive_streaks:
                old_streak = streak.current_streak
                streak.reset_streak()
                reset_count += 1
                self.stdout.write(
                    f'Reset streak for {streak.user.firstName} {streak.user.lastName} '
                    f'(was: {old_streak}, now: {streak.current_streak})'
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully reset {reset_count} inactive streaks.')
            )
