import json
from django.core.management.base import BaseCommand
from django.conf import settings
from dspace_integration.services.dspace_client import DSpaceClient
from dspace_integration.services.metadata_parser import MetadataParser

class Command(BaseCommand):
    help = "Inspects and verifies the live Kabale University DSpace REST API endpoints and metadata schema."

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-size',
            type=int,
            default=5,
            help='Number of sample research items to inspect (default: 5)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("  KABALE UNIVERSITY DSPACE REST API INSPECTION UTILITY"))
        self.stdout.write(self.style.SUCCESS("=" * 80))

        client = DSpaceClient()
        target_comm_uuid = settings.DSPACE_TARGET_COMMUNITY_UUID
        sample_size = options['sample_size']

        self.stdout.write(f"Target Base URL: {client.base_url}")
        self.stdout.write(f"Repository Frontend: {settings.DSPACE_REPOSITORY_FRONTEND}")
        self.stdout.write(f"Target Community UUID: {target_comm_uuid}")

        # 1. Test Connectivity
        self.stdout.write("\n[1/6] Testing API Connectivity...")
        conn_res = client.test_connection()
        if conn_res['status'] == 'connected':
            self.stdout.write(self.style.SUCCESS(f"  [OK] Successfully connected to DSpace REST API (HTTP 200)"))
        else:
            self.stdout.write(self.style.ERROR(f"  [FAIL] Failed connecting to DSpace: {conn_res.get('error')}"))
            return

        # 2. Inspect Communities
        self.stdout.write("\n[2/6] Inspecting Top-Level Communities...")
        try:
            comm_data = client.get_communities(size=10)
            communities = comm_data.get('_embedded', {}).get('communities', [])
            self.stdout.write(f"  Found {len(communities)} top-level communities on this page:")
            for c in communities:
                name = c.get('name')
                uuid = c.get('uuid')
                self.stdout.write(f"   - {name} (UUID: {uuid})")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Warning fetching communities: {e}"))

        # 3. Inspect Target Postgraduate Community
        self.stdout.write(f"\n[3/6] Inspecting Target Community ({target_comm_uuid})...")
        try:
            target_comm = client.get_community(target_comm_uuid)
            self.stdout.write(self.style.SUCCESS(f"  Target Community Name: {target_comm.get('name')}"))
            self.stdout.write(f"  Handle: {target_comm.get('handle', 'N/A')}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error fetching target community: {e}"))

        # 4. Inspect Collections under Community
        self.stdout.write("\n[4/6] Inspecting Collections within Target Community...")
        try:
            colls_resp = client.get_community_collections(target_comm_uuid, size=50)
            colls = colls_resp.get('_embedded', {}).get('collections', [])
            self.stdout.write(self.style.SUCCESS(f"  Found {len(colls)} Collections (Faculties/Institutes):"))
            for i, col in enumerate(colls, 1):
                name = col.get('name')
                c_uuid = col.get('uuid')
                handle = col.get('handle', 'N/A')
                self.stdout.write(f"   {i:2d}. {name}")
                self.stdout.write(f"       UUID: {c_uuid} | Handle: {handle}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error fetching collections: {e}"))

        # 5. Inspect Discovery API & Pagination
        self.stdout.write(f"\n[5/6] Inspecting DSpace Discovery API (/discover/search/objects)...")
        try:
            disc_resp = client.get_discovery_results(scope=target_comm_uuid, page=0, size=sample_size)
            page_info = disc_resp.get('_embedded', {}).get('searchResult', {}).get('page', {})
            total_elements = page_info.get('totalElements', 0)
            total_pages = page_info.get('totalPages', 0)
            self.stdout.write(self.style.SUCCESS(f"  Discovery API Active!"))
            self.stdout.write(f"  Total Indexed Elements: {total_elements}")
            self.stdout.write(f"  Total Pages (at size {sample_size}): {total_pages}")
            self.stdout.write(f"  Current Page: {page_info.get('number', 0)}")

            # 6. Sample Research Records & Metadata Fields
            self.stdout.write(f"\n[6/6] Inspecting {sample_size} Sample Records and Metadata Fields...")
            objects = disc_resp.get('_embedded', {}).get('searchResult', {}).get('_embedded', {}).get('objects', [])
            parser = MetadataParser()
            for idx, obj in enumerate(objects, 1):
                indexable = obj.get('_embedded', {}).get('indexableObject', {})
                parsed = parser.parse_item(indexable)
                self.stdout.write("-" * 80)
                self.stdout.write(self.style.SUCCESS(f"  Record #{idx}: {parsed['title']}"))
                self.stdout.write(f"  DSpace UUID: {parsed['dspace_uuid']}")
                self.stdout.write(f"  Handle: {parsed['handle']}")
                self.stdout.write(f"  Authors: {parsed['authors_display']}")
                self.stdout.write(f"  Publication Year: {parsed['publication_year']} (Date: {parsed['date_issued']})")
                self.stdout.write(f"  Keywords/Subjects: {', '.join(parsed['keywords']) if parsed['keywords'] else 'None'}")
                self.stdout.write(f"  Abstract Preview: {parsed['abstract'][:150]}..." if parsed['abstract'] else "  Abstract: [Not provided]")
                self.stdout.write(f"  DSpace Direct URL: {parsed['dspace_url']}")
                self.stdout.write(f"  All Metadata Keys Present: {list(parsed['metadata_json'].keys())}")

            self.stdout.write("=" * 80)
            self.stdout.write(self.style.SUCCESS("  INSPECTION COMPLETED SUCCESSFULLY"))
            self.stdout.write("=" * 80)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error inspecting discovery objects: {e}"))
