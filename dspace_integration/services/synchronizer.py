import time
import logging
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from research.models import Faculty, Collection, Researcher, ResearchItem, SyncLog
from .dspace_client import DSpaceClient, DSpaceClientError
from .metadata_parser import MetadataParser

logger = logging.getLogger(__name__)

class DSpaceSynchronizer:
    """
    Orchestrates synchronization of research metadata from Kabale University DSpace into the local database.
    """
    def __init__(self, target_community_uuid=None, page_size=None):
        self.client = DSpaceClient()
        self.parser = MetadataParser()
        self.community_uuid = target_community_uuid or settings.DSPACE_TARGET_COMMUNITY_UUID
        self.page_size = page_size or settings.DSPACE_PAGE_SIZE

    def sync_collections_and_faculties(self):
        """
        Synchronizes the faculties and collections under the target postgraduate community.
        Returns a map of {collection_uuid: {name, faculty_obj, collection_obj}}.
        """
        collection_map = {}
        try:
            colls_resp = self.client.get_community_collections(self.community_uuid, size=100)
            colls = colls_resp.get('_embedded', {}).get('collections', [])
            
            for col in colls:
                c_uuid = col.get('uuid')
                c_name = col.get('name', 'General Collection').strip()
                c_handle = col.get('handle', '')
                
                # Derive Faculty from collection name
                faculty_name = c_name
                faculty_code = ''
                if '(' in c_name and ')' in c_name:
                    code_part = c_name[c_name.rfind('(')+1:c_name.rfind(')')].strip()
                    faculty_code = code_part

                with transaction.atomic():
                    faculty, _ = Faculty.objects.get_or_create(
                        name=faculty_name,
                        defaults={'code': faculty_code, 'dspace_collection_uuid': c_uuid}
                    )
                    
                    collection, _ = Collection.objects.update_or_create(
                        dspace_uuid=c_uuid,
                        defaults={
                            'name': c_name,
                            'handle': c_handle,
                            'faculty': faculty,
                            'community_name': 'Postgraduate Masters Theses/Reports'
                        }
                    )
                
                collection_map[c_uuid] = {
                    'name': c_name,
                    'faculty_name': faculty_name,
                    'faculty_obj': faculty,
                    'collection_obj': collection
                }
            logger.info(f"Synchronized {len(collection_map)} faculties and collections.")
        except Exception as e:
            logger.warning(f"Could not sync collections hierarchy directly: {e}. Will infer from item metadata.")
            # Build map from existing database records if available
            for c in Collection.objects.select_related('faculty').all():
                collection_map[c.dspace_uuid] = {
                    'name': c.name,
                    'faculty_name': c.faculty.name if c.faculty else c.name,
                    'faculty_obj': c.faculty,
                    'collection_obj': c
                }
        return collection_map

    def sync_records(self, max_pages=None, progress_callback=None):
        """
        Executes complete metadata synchronization with pagination and error recovery.
        """
        start_time = time.time()
        sync_log = SyncLog.objects.create(
            status='in_progress',
            started_at=timezone.now()
        )

        records_discovered = 0
        records_created = 0
        records_updated = 0
        unchanged_records = 0
        duplicates_skipped = 0
        errors = []

        try:
            # 1. First sync faculties and collections
            collection_map = self.sync_collections_and_faculties()

            # 2. Determine total records and pages using Discovery API
            first_page = self.client.get_discovery_results(
                scope=self.community_uuid,
                page=0,
                size=self.page_size
            )
            
            page_info = first_page.get('_embedded', {}).get('searchResult', {}).get('page', {})
            total_elements = page_info.get('totalElements', 0)
            total_pages = page_info.get('totalPages', 1)
            records_discovered = total_elements

            if max_pages:
                total_pages = min(total_pages, max_pages)

            logger.info(f"Discovered {total_elements} total research records across {total_pages} pages.")

            # 3. Iterate over pages
            current_page = 0
            while current_page < total_pages:
                try:
                    if current_page == 0:
                        page_data = first_page
                    else:
                        page_data = self.client.get_discovery_results(
                            scope=self.community_uuid,
                            page=current_page,
                            size=self.page_size
                        )

                    objects = page_data.get('_embedded', {}).get('searchResult', {}).get('_embedded', {}).get('objects', [])
                    
                    for obj in objects:
                        try:
                            indexable = obj.get('_embedded', {}).get('indexableObject', {})
                            item_uuid = indexable.get('uuid')
                            if not item_uuid:
                                continue

                            parsed = self.parser.parse_item(indexable, collection_map=collection_map)
                            
                            # Resolve faculty and collection objects
                            col_info = collection_map.get(parsed['collection_uuid'])
                            faculty_obj = col_info['faculty_obj'] if col_info else None
                            collection_obj = col_info['collection_obj'] if col_info else None
                            
                            if not faculty_obj and parsed['faculty_name']:
                                faculty_obj = Faculty.objects.filter(name=parsed['faculty_name']).first()
                            
                            # Check if record already exists
                            existing = ResearchItem.objects.filter(dspace_uuid=item_uuid).first()
                            
                            is_new = False
                            is_updated = False
                            
                            if existing is None:
                                item = ResearchItem(
                                    dspace_uuid=item_uuid,
                                    title=parsed['title'],
                                    abstract=parsed['abstract'],
                                    authors_display=parsed['authors_display'],
                                    subjects=parsed['subjects'],
                                    keywords=parsed['keywords'],
                                    publication_year=parsed['publication_year'],
                                    date_issued=parsed['date_issued'],
                                    faculty=faculty_obj,
                                    faculty_name=parsed['faculty_name'],
                                    collection=collection_obj,
                                    collection_name=parsed['collection_name'],
                                    community='Postgraduate Masters Theses/Reports',
                                    community_uuid=self.community_uuid,
                                    handle=parsed['handle'],
                                    dspace_url=parsed['dspace_url'],
                                    item_type=parsed['item_type'],
                                    metadata_json=parsed['metadata_json'],
                                    search_vector_text=parsed['search_vector_text'],
                                )
                                item.save()
                                is_new = True
                                records_created += 1
                            else:
                                # Check if changed
                                has_changed = (
                                    existing.title != parsed['title'] or
                                    existing.abstract != parsed['abstract'] or
                                    existing.handle != parsed['handle'] or
                                    existing.faculty_name != parsed['faculty_name']
                                )
                                if has_changed:
                                    existing.title = parsed['title']
                                    existing.abstract = parsed['abstract']
                                    existing.authors_display = parsed['authors_display']
                                    existing.subjects = parsed['subjects']
                                    existing.keywords = parsed['keywords']
                                    existing.publication_year = parsed['publication_year']
                                    existing.date_issued = parsed['date_issued']
                                    if faculty_obj:
                                        existing.faculty = faculty_obj
                                    if parsed['faculty_name']:
                                        existing.faculty_name = parsed['faculty_name']
                                    if collection_obj:
                                        existing.collection = collection_obj
                                    existing.handle = parsed['handle']
                                    existing.dspace_url = parsed['dspace_url']
                                    existing.metadata_json = parsed['metadata_json']
                                    existing.search_vector_text = parsed['search_vector_text']
                                    existing.save()
                                    item = existing
                                    is_updated = True
                                    records_updated += 1
                                else:
                                    existing.save(update_fields=['last_synced'])
                                    item = existing
                                    unchanged_records += 1

                            # Synchronize Researcher relation
                            author_objs = []
                            for author_raw in parsed['authors']:
                                clean_name = author_raw.strip()
                                norm_name = self.parser.normalize_author_name(clean_name)
                                if norm_name:
                                    researcher, _ = Researcher.objects.get_or_create(
                                        normalized_name=norm_name,
                                        defaults={'name': clean_name}
                                    )
                                    author_objs.append(researcher)
                            
                            if author_objs:
                                item.authors.set(author_objs)

                        except Exception as record_err:
                            err_msg = f"Error processing item on page {current_page}: {str(record_err)}"
                            logger.error(err_msg)
                            errors.append(err_msg)

                    if progress_callback:
                        progress_callback(current_page + 1, total_pages, records_created, records_updated)

                except Exception as page_err:
                    err_msg = f"Error fetching discovery page {current_page}: {str(page_err)}"
                    logger.error(err_msg)
                    errors.append(err_msg)

                current_page += 1

            # Update researcher research counts
            for r in Researcher.objects.all():
                c = r.research_items.count()
                if r.research_count != c:
                    r.research_count = c
                    r.save(update_fields=['research_count'])

            # Update collection item counts
            for col in Collection.objects.all():
                col.item_count = col.research_items.count()
                col.save(update_fields=['item_count'])

            duration = round(time.time() - start_time, 2)
            final_status = 'success' if len(errors) == 0 else ('partial' if (records_created + records_updated + unchanged_records) > 0 else 'failed')

            sync_log.completed_at = timezone.now()
            sync_log.records_retrieved = records_discovered
            sync_log.records_created = records_created
            sync_log.records_updated = records_updated
            sync_log.duplicates_skipped = unchanged_records
            sync_log.errors_count = len(errors)
            sync_log.duration_seconds = duration
            sync_log.status = final_status
            sync_log.error_details = '\n'.join(errors[:20])
            sync_log.summary_json = {
                'records_discovered': records_discovered,
                'new_records': records_created,
                'updated_records': records_updated,
                'unchanged_records': unchanged_records,
                'errors': len(errors),
                'duration': duration,
                'status': final_status
            }
            sync_log.save()

            return {
                'status': final_status,
                'records_discovered': records_discovered,
                'new_records': records_created,
                'updated_records': records_updated,
                'unchanged_records': unchanged_records,
                'errors': len(errors),
                'duration': duration,
                'error_messages': errors[:10]
            }

        except Exception as fatal_err:
            duration = round(time.time() - start_time, 2)
            sync_log.completed_at = timezone.now()
            sync_log.status = 'failed'
            sync_log.duration_seconds = duration
            sync_log.errors_count = len(errors) + 1
            sync_log.error_details = f"Fatal synchronization error: {str(fatal_err)}\n" + '\n'.join(errors[:10])
            sync_log.save()
            raise
