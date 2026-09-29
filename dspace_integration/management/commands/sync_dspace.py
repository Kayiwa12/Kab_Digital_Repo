from django.core.management.base import BaseCommand
from django.conf import settings
from dspace_integration.services.synchronizer import DSpaceSynchronizer

class Command(BaseCommand):
    help = "Synchronizes research records from Kabale University DSpace into the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-pages',
            type=int,
            default=None,
            help='Limit the number of discovery pages to synchronize (optional, for partial/testing runs)'
        )
        parser.add_argument(
            '--page-size',
            type=int,
            default=None,
            help='Override discovery page size (default: 20)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("  KABALE UNIVERSITY IDR SYNCHRONIZATION"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(f"Connecting to DSpace API at: {settings.DSPACE_API_BASE_URL}")
        self.stdout.write(f"Target Community: {settings.DSPACE_TARGET_COMMUNITY_UUID}")

        synchronizer = DSpaceSynchronizer(
            target_community_uuid=settings.DSPACE_TARGET_COMMUNITY_UUID,
            page_size=options.get('page_size')
        )

        def progress_callback(page_num, total_pages, created, updated):
            self.stdout.write(f"  Progress: Page {page_num}/{total_pages} processed... (New: {created}, Updated: {updated})")

        self.stdout.write("Starting synchronization...")

        try:
            summary = synchronizer.sync_records(
                max_pages=options.get('max_pages'),
                progress_callback=progress_callback
            )

            self.stdout.write("\n" + self.style.SUCCESS("Connected to DSpace successfully."))
            self.stdout.write(f"Records discovered: {summary['records_discovered']}")
            self.stdout.write(f"New records: {summary['new_records']}")
            self.stdout.write(f"Updated records: {summary['updated_records']}")
            self.stdout.write(f"Unchanged records: {summary['unchanged_records']}")
            self.stdout.write(f"Errors: {summary['errors']}")
            self.stdout.write(f"Duration: {summary['duration']} seconds")
            
            if summary['errors'] > 0:
                self.stdout.write(self.style.WARNING("Some non-fatal errors occurred during synchronization:"))
                for err in summary['error_messages']:
                    self.stdout.write(self.style.WARNING(f"  - {err}"))
                self.stdout.write(self.style.WARNING("Synchronization completed with partial notices."))
            else:
                self.stdout.write(self.style.SUCCESS("Synchronization completed successfully."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Synchronization failed: {str(e)}"))
            raise
