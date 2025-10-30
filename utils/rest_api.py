#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rest_api.py — GeoDocs REST API client
"""
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class GeodocsAPI:
    """Client for GeoDocs REST API"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.base_url = ""
        self.timeout = 20
        self.verify_tls = True
        self.auth_type = "jwt"
        self.jwt_token = ""
        self.iiif_base_url = ""
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.base_url = config.get('api_base_url', '')
            self.timeout = config.get('timeout_sec', 20)
            self.verify_tls = config.get('verify_tls', True)
            self.auth_type = config.get('auth', 'jwt')
            self.jwt_token = config.get('jwt_token', '')
            self.iiif_base_url = config.get('iiif_image_base_url', '')
        except Exception as e:
            print(f"Error loading API config: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with authentication"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        if self.auth_type == 'jwt' and self.jwt_token:
            headers['Authorization'] = f'Bearer {self.jwt_token}'
        
        return headers
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API"""
        if not REQUESTS_AVAILABLE:
            return {'error': 'requests library not available'}
        
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout,
                verify=self.verify_tls
            )
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            return {'error': str(e)}
    
    # Places API
    def search_places(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for places by name"""
        result = self._request('GET', '/places/search', params={'q': query, 'limit': limit})
        return result.get('results', []) if isinstance(result, dict) else []
    
    def get_place(self, place_id: int) -> Optional[Dict]:
        """Get place details by ID"""
        result = self._request('GET', f'/places/{place_id}')
        return result if not result.get('error') else None
    
    def create_place(self, data: Dict) -> Optional[Dict]:
        """Create new place"""
        result = self._request('POST', '/places', data=data)
        return result if not result.get('error') else None
    
    # Persons API
    def search_persons(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for persons by name"""
        result = self._request('GET', '/persons/search', params={'q': query, 'limit': limit})
        return result.get('results', []) if isinstance(result, dict) else []
    
    def get_person(self, person_id: int) -> Optional[Dict]:
        """Get person details by ID"""
        result = self._request('GET', f'/persons/{person_id}')
        return result if not result.get('error') else None
    
    def create_person(self, data: Dict) -> Optional[Dict]:
        """Create new person"""
        result = self._request('POST', '/persons', data=data)
        return result if not result.get('error') else None
    
    # Documents API
    def search_documents(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for documents"""
        result = self._request('GET', '/documents/search', params={'q': query, 'limit': limit})
        return result.get('results', []) if isinstance(result, dict) else []
    
    def get_document(self, doc_id: int) -> Optional[Dict]:
        """Get document details by ID"""
        result = self._request('GET', f'/documents/{doc_id}')
        return result if not result.get('error') else None
    
    def create_document(self, data: Dict) -> Optional[Dict]:
        """Create new document"""
        result = self._request('POST', '/documents', data=data)
        return result if not result.get('error') else None
    
    def upload_document_image(self, doc_id: int, image_path: str) -> Optional[Dict]:
        """Upload image for document"""
        if not REQUESTS_AVAILABLE:
            return None
        
        url = f"{self.base_url}/documents/{doc_id}/images"
        headers = self._get_headers()
        del headers['Content-Type']  # Let requests set it for multipart
        
        try:
            with open(image_path, 'rb') as f:
                files = {'image': f}
                response = requests.post(
                    url,
                    files=files,
                    headers=headers,
                    timeout=self.timeout,
                    verify=self.verify_tls
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {'error': str(e)}
    
    # Annotations API
    def get_annotations(self, doc_id: int) -> List[Dict]:
        """Get annotations for document"""
        result = self._request('GET', f'/documents/{doc_id}/annotations')
        return result.get('annotations', []) if isinstance(result, dict) else []
    
    def create_annotation(self, doc_id: int, data: Dict) -> Optional[Dict]:
        """Create annotation for document"""
        result = self._request('POST', f'/documents/{doc_id}/annotations', data=data)
        return result if not result.get('error') else None
    
    def update_annotation(self, annotation_id: int, data: Dict) -> Optional[Dict]:
        """Update annotation"""
        result = self._request('PUT', f'/annotations/{annotation_id}', data=data)
        return result if not result.get('error') else None
    
    def delete_annotation(self, annotation_id: int) -> bool:
        """Delete annotation"""
        result = self._request('DELETE', f'/annotations/{annotation_id}')
        return not result.get('error')
    
    # Geodata API
    def geocode(self, address: str) -> Optional[Dict]:
        """Geocode address to coordinates"""
        result = self._request('GET', '/geo/geocode', params={'address': address})
        return result if not result.get('error') else None
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[Dict]:
        """Reverse geocode coordinates to address"""
        result = self._request('GET', '/geo/reverse', params={'lat': lat, 'lon': lon})
        return result if not result.get('error') else None
    
    # IIIF
    def get_iiif_image_url(
        self,
        image_id: str,
        region: str = 'full',
        size: str = 'full',
        rotation: int = 0,
        quality: str = 'default',
        format: str = 'jpg'
    ) -> str:
        """
        Generate IIIF Image API URL
        
        See: https://iiif.io/api/image/3.0/
        """
        return f"{self.iiif_base_url}/{image_id}/{region}/{size}/{rotation}/{quality}.{format}"
    
    # Health check
    def ping(self) -> bool:
        """Check if API is accessible"""
        result = self._request('GET', '/health')
        return not result.get('error')


# Global instance
_api_client = None


def get_api_client(config_path: Optional[str] = None) -> GeodocsAPI:
    """Get or create global API client"""
    global _api_client
    if _api_client is None:
        _api_client = GeodocsAPI(config_path)
    return _api_client
