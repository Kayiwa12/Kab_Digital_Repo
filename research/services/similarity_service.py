import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from research.models import ResearchItem

logger = logging.getLogger(__name__)

class SimilarityService:
    """
    Computes text and metadata similarity using TF-IDF vectorization and Cosine Similarity.
    No generative AI or external LLM APIs are used.
    """
    _cached_matrix = None
    _cached_item_ids = None
    _cached_vectorizer = None
    _cached_feature_names = None
    _last_record_count = 0

    @classmethod
    def _build_corpus(cls):
        """Retrieves and prepares text representations from indexed research items."""
        items = list(ResearchItem.objects.all().order_by('id'))
        corpus = []
        item_ids = []

        for it in items:
            keywords_text = ' '.join(it.keywords or [])
            subjects_text = ' '.join(it.subjects or [])
            # Boost title and keywords by repeating them
            combined = f"{it.title} {it.title} {keywords_text} {keywords_text} {subjects_text} {it.faculty_name} {it.abstract}"
            # Clean string
            cleaned = re.sub(r'[^\w\s]', ' ', combined.lower())
            corpus.append(cleaned)
            item_ids.append(it.id)

        return items, item_ids, corpus

    @classmethod
    def refresh_model(cls):
        """Builds or rebuilds the TF-IDF matrix."""
        items, item_ids, corpus = cls._build_corpus()
        if not corpus:
            cls._cached_matrix = None
            cls._cached_item_ids = []
            cls._cached_vectorizer = None
            cls._cached_feature_names = []
            cls._last_record_count = 0
            return

        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            max_features=10000
        )
        matrix = vectorizer.fit_transform(corpus)

        cls._cached_matrix = matrix
        cls._cached_item_ids = item_ids
        cls._cached_vectorizer = vectorizer
        cls._cached_feature_names = vectorizer.get_feature_names_out()
        cls._last_record_count = len(items)
        logger.info(f"TF-IDF model initialized with {len(items)} records and {matrix.shape[1]} features.")

    @classmethod
    def get_similar_items(cls, target_item, top_n=6):
        """
        Finds the most similar research records to target_item using Cosine Similarity.
        Returns a list of dicts: [{'item': ResearchItem, 'score': float, 'matching_terms': list}].
        """
        current_count = ResearchItem.objects.count()
        if cls._cached_matrix is None or cls._last_record_count != current_count:
            cls.refresh_model()

        if cls._cached_matrix is None or not cls._cached_item_ids:
            return []

        try:
            target_idx = cls._cached_item_ids.index(target_item.id)
        except ValueError:
            # Item might not be in cache yet, refresh
            cls.refresh_model()
            try:
                target_idx = cls._cached_item_ids.index(target_item.id)
            except ValueError:
                return []

        # Calculate cosine similarity for target row against all rows
        target_vector = cls._cached_matrix[target_idx]
        sim_scores = cosine_similarity(target_vector, cls._cached_matrix).flatten()

        # Target item will have similarity 1.0 with itself, so exclude it
        ranked_indices = sim_scores.argsort()[::-1]

        target_keywords = set(k.lower() for k in target_item.all_keywords())
        target_words = set(re.findall(r'\b[a-z]{4,}\b', target_item.title.lower()))

        results = []
        item_cache = {it.id: it for it in ResearchItem.objects.filter(
            id__in=[cls._cached_item_ids[i] for i in ranked_indices[:top_n+5] if i != target_idx]
        ).select_related('faculty', 'collection')}

        for idx in ranked_indices:
            if idx == target_idx:
                continue
            item_id = cls._cached_item_ids[idx]
            score = float(sim_scores[idx])

            # Stop if similarity is negligible (< 0.05) or enough items gathered
            if score < 0.02 and len(results) >= 2:
                break

            matched_item = item_cache.get(item_id)
            if not matched_item:
                continue

            # Identify matching conceptual terms
            matched_keywords = set(k.lower() for k in matched_item.all_keywords())
            shared_kw = list(target_keywords.intersection(matched_keywords))
            
            # Shared significant title words
            matched_title_words = set(re.findall(r'\b[a-z]{4,}\b', matched_item.title.lower()))
            shared_title = list(target_words.intersection(matched_title_words))
            
            common_terms = list(dict.fromkeys(shared_kw + shared_title))[:4]

            results.append({
                'item': matched_item,
                'score': round(score * 100, 1),
                'score_normalized': min(100, round(score * 115, 1)), # scale for user visual clarity
                'common_terms': common_terms,
            })

            if len(results) >= top_n:
                break

        return results
