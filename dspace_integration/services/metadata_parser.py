import re
import logging

logger = logging.getLogger(__name__)

class MetadataParser:
    """
    Parses and normalizes raw metadata returned by Kabale University DSpace 9.x REST API.
    """

    @staticmethod
    def extract_values(metadata_dict, field_name):
        """Extracts list of text values for a given metadata field name."""
        if not metadata_dict or field_name not in metadata_dict:
            return []
        items = metadata_dict.get(field_name, [])
        if not isinstance(items, list):
            return []
        values = []
        for item in items:
            if isinstance(item, dict) and 'value' in item:
                val = str(item['value']).strip()
                if val:
                    values.append(val)
            elif isinstance(item, str) and item.strip():
                values.append(item.strip())
        return values

    @staticmethod
    def extract_first(metadata_dict, field_name, default=''):
        """Extracts the first value for a metadata field."""
        vals = MetadataParser.extract_values(metadata_dict, field_name)
        return vals[0] if vals else default

    @classmethod
    def parse_item(cls, item_data, collection_map=None):
        """
        Extracts and normalizes fields from a DSpace item or indexableObject.
        """
        metadata = item_data.get('metadata', {})
        uuid = item_data.get('uuid', '')
        handle = item_data.get('handle', '') or cls.extract_first(metadata, 'dc.identifier.uri')
        
        # Handle might be URI like http://hdl.handle.net/20.500.12493/1168 or just 20.500.12493/1168
        if handle and 'handle.net/' in handle:
            handle = handle.split('handle.net/')[-1]
        elif handle and 'idr.kab.ac.ug/handle/' in handle:
            handle = handle.split('idr.kab.ac.ug/handle/')[-1]

        # 1. Title
        title = cls.extract_first(metadata, 'dc.title') or item_data.get('name') or 'Untitled Research Record'
        # Clean title trailing colons or excess whitespace
        title = title.strip().rstrip(':')

        # 2. Authors
        authors = cls.extract_values(metadata, 'dc.contributor.author')
        if not authors:
            authors = cls.extract_values(metadata, 'dc.creator')
        authors_display = '; '.join(authors) if authors else 'Author Not Specified'

        # 3. Abstract
        abstract = cls.extract_first(metadata, 'dc.description.abstract')
        if not abstract:
            abstract = cls.extract_first(metadata, 'dc.description')

        # 4. Subjects & Keywords
        subjects = cls.extract_values(metadata, 'dc.subject')
        # Additional keyword fields if present
        extra_keywords = cls.extract_values(metadata, 'dc.subject.other')
        
        # Normalize and deduplicate keywords
        cleaned_keywords = []
        seen_kw = set()
        for kw in (subjects + extra_keywords):
            # Split comma-separated keywords if author placed multiple in one entry
            parts = [p.strip() for p in re.split(r'[,;]\s*', kw) if p.strip()]
            for p in parts:
                clean_p = p.strip()
                if clean_p and clean_p.lower() not in seen_kw and len(clean_p) > 1:
                    seen_kw.add(clean_p.lower())
                    cleaned_keywords.append(clean_p)

        # 5. Publication year and date issued
        date_issued = cls.extract_first(metadata, 'dc.date.issued') or cls.extract_first(metadata, 'dc.date.accessioned')
        publication_year = None
        if date_issued:
            # Match 4 digits for year
            year_match = re.search(r'\b(19\d\d|20\d\d)\b', date_issued)
            if year_match:
                try:
                    publication_year = int(year_match.group(1))
                except ValueError:
                    publication_year = None

        # 6. Item Type
        item_type = cls.extract_first(metadata, 'dc.type') or 'Thesis'

        # 7. Collection / Faculty Association
        collection_name = ''
        collection_uuid = ''
        faculty_name = ''
        
        # Check owningCollection in links
        links = item_data.get('_links', {})
        owning_col_link = links.get('owningCollection', {}).get('href', '')
        
        if collection_map and owning_col_link:
            # Check if owning collection uuid is in href
            for cuuid, cinfo in collection_map.items():
                if cuuid in owning_col_link:
                    collection_uuid = cuuid
                    collection_name = cinfo.get('name', '')
                    faculty_name = cinfo.get('faculty_name', collection_name)
                    break

        # If not resolved from map, check metadata publisher or department
        if not faculty_name:
            publisher = cls.extract_first(metadata, 'dc.publisher')
            if 'Faculty' in publisher or 'Institute' in publisher:
                faculty_name = publisher

        # 8. Direct URLs
        dspace_url = ''
        if handle:
            dspace_url = f"https://idr.kab.ac.ug/handle/{handle}"
        elif uuid:
            dspace_url = f"https://backend.kab.ac.ug/server/api/core/items/{uuid}"

        # 9. Search vector text (for fast TF-IDF and local search)
        text_parts = [
            title,
            abstract,
            authors_display,
            ' '.join(cleaned_keywords),
            faculty_name,
            str(publication_year or '')
        ]
        search_vector_text = ' '.join(filter(None, text_parts))

        return {
            'dspace_uuid': uuid,
            'title': title,
            'abstract': abstract,
            'authors': authors,
            'authors_display': authors_display,
            'subjects': subjects,
            'keywords': cleaned_keywords,
            'publication_year': publication_year,
            'date_issued': date_issued,
            'collection_uuid': collection_uuid,
            'collection_name': collection_name,
            'faculty_name': faculty_name,
            'handle': handle,
            'dspace_url': dspace_url,
            'item_type': item_type,
            'metadata_json': metadata,
            'search_vector_text': search_vector_text,
        }

    @staticmethod
    def normalize_author_name(author_str):
        """
        Normalizes author name for deduplication.
        e.g. 'Tumuheirwe, Kizito' -> 'tumuheirwe kizito'
        """
        if not author_str:
            return ''
        cleaned = re.sub(r'[^\w\s]', ' ', author_str).lower()
        tokens = [t.strip() for t in cleaned.split() if t.strip()]
        return ' '.join(tokens)
