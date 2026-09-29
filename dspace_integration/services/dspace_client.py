import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class DSpaceClientError(Exception):
    """Base exception for DSpace API client errors."""
    pass

class DSpaceConnectionError(DSpaceClientError):
    """Raised when unable to connect to the DSpace REST API."""
    pass

class DSpaceResourceNotFoundError(DSpaceClientError):
    """Raised when a requested resource is not found (404)."""
    pass

class DSpaceClient:
    """
    Robust REST API client for Kabale University's Institutional Digital Repository (DSpace 9.x).
    """
    def __init__(self, base_url=None, timeout=None):
        self.base_url = (base_url or settings.DSPACE_API_BASE_URL).rstrip('/')
        self.timeout = timeout or settings.DSPACE_REQUEST_TIMEOUT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Kabale-IDR-DiscoveryPlatform/1.0 (+https://idr.kab.ac.ug)',
            'Accept': 'application/hal+json, application/json',
        })

    def _request(self, method, endpoint, params=None, **kwargs):
        """Internal helper for executing requests with error handling."""
        url = endpoint if endpoint.startswith('http') else f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=self.timeout,
                **kwargs
            )
            if response.status_code == 404:
                raise DSpaceResourceNotFoundError(f"DSpace resource not found at {url}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to DSpace API at {url}: {e}")
            raise DSpaceConnectionError(f"DSpace request timed out after {self.timeout}s: {url}") from e
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to DSpace API at {url}: {e}")
            raise DSpaceConnectionError(f"Unable to connect to DSpace server at {url}: {e}") from e
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from DSpace API ({e.response.status_code}) at {url}: {e}")
            raise DSpaceClientError(f"DSpace API returned HTTP {e.response.status_code}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error communicating with DSpace at {url}: {e}")
            raise DSpaceClientError(f"Unexpected DSpace client error: {e}") from e

    def test_connection(self):
        """Verifies connectivity to the DSpace REST API."""
        try:
            data = self._request('GET', 'core/communities', params={'size': 1})
            return {
                'status': 'connected',
                'base_url': self.base_url,
                'status_code': 200,
                'has_data': '_embedded' in data
            }
        except Exception as e:
            return {
                'status': 'error',
                'base_url': self.base_url,
                'error': str(e)
            }

    def get_communities(self, page=0, size=20):
        """Fetches top-level communities from DSpace."""
        return self._request('GET', 'core/communities', params={'page': page, 'size': size})

    def get_community(self, community_uuid):
        """Fetches a specific community by UUID."""
        return self._request('GET', f'core/communities/{community_uuid}')

    def get_community_collections(self, community_uuid, page=0, size=50):
        """Fetches all collections under a specific community."""
        return self._request('GET', f'core/communities/{community_uuid}/collections', params={'page': page, 'size': size})

    def get_collection(self, collection_uuid):
        """Fetches metadata for a specific collection."""
        return self._request('GET', f'core/collections/{collection_uuid}')

    def get_item(self, item_uuid):
        """Fetches a single item record from DSpace."""
        return self._request('GET', f'core/items/{item_uuid}')

    def get_item_bundles(self, item_uuid):
        """Fetches bundles (content files/bitstreams) for an item."""
        try:
            return self._request('GET', f'core/items/{item_uuid}/bundles')
        except Exception as e:
            logger.warning(f"Could not fetch bundles for item {item_uuid}: {e}")
            return {}

    def get_discovery_results(self, scope=None, query=None, page=0, size=20, sort=None, filters=None):
        """
        Queries the DSpace 9 Discovery API (/discover/search/objects).
        """
        params = {
            'page': page,
            'size': size,
        }
        if scope:
            params['scope'] = scope
        if query:
            params['query'] = query
        if sort:
            params['sort'] = sort
        if filters:
            for k, v in filters.items():
                params[k] = v

        return self._request('GET', 'discover/search/objects', params=params)
