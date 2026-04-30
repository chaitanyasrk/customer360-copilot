"""
Metadata Cache Service — In-memory + disk-persisted cache for Salesforce object metadata.

Uses the Salesforce describe() API to dynamically discover object schemas,
then caches the results to avoid repeated API calls. Supports TTL-based
expiration and JSON file persistence.
"""
import json
import os
import threading
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.config import settings


class MetadataCache:
    """In-memory + disk-persisted cache for Salesforce object describe() metadata"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._cache_dir = settings.METADATA_CACHE_DIR
        self._ttl_hours = settings.METADATA_CACHE_TTL_HOURS
        self._objects = [
            obj.strip()
            for obj in settings.METADATA_OBJECTS.split(",")
        ]

        # Ensure cache directory exists
        os.makedirs(self._cache_dir, exist_ok=True)

        # Load any existing disk cache on init
        self._load_from_disk()
        print(f"📦 MetadataCache initialized — objects: {self._objects}, TTL: {self._ttl_hours}h")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_object_metadata(self, object_name: str) -> Optional[Dict[str, Any]]:
        """
        Returns cached metadata for a Salesforce object.
        On cache miss, fetches via describe() and persists.

        Returns:
            Dict with keys: object_name, fields, relationships, label, key_prefix, fetched_at
            or None if the object cannot be described.
        """
        with self._lock:
            # Check in-memory cache (with TTL)
            if self._is_cache_valid(object_name):
                return self._cache[object_name]

        # Cache miss — fetch from Salesforce
        metadata = self._fetch_metadata(object_name)
        if metadata:
            with self._lock:
                self._cache[object_name] = metadata
                self._timestamps[object_name] = time.time()
            self._save_to_disk(object_name, metadata)

        return metadata

    def get_queryable_fields(self, object_name: str) -> List[Dict[str, Any]]:
        """
        Returns only queryable fields with useful attributes.

        Each field dict contains:
            name, label, type, length, referenceTo, isFilterable, relationshipName
        """
        metadata = self.get_object_metadata(object_name)
        if not metadata:
            return []
        return metadata.get("fields", [])

    def get_relationship_fields(self, object_name: str) -> List[Dict[str, Any]]:
        """Returns lookup / master-detail relationship fields."""
        metadata = self.get_object_metadata(object_name)
        if not metadata:
            return []
        return metadata.get("relationships", [])

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Returns metadata for all configured objects (fetching if needed)."""
        result = {}
        for obj in self._objects:
            md = self.get_object_metadata(obj)
            if md:
                result[obj] = md
        return result

    def get_metadata_for_prompt(self, object_names: List[str] = None) -> str:
        """
        Returns a compact text representation of object schemas,
        suitable for inclusion in an LLM prompt.
        """
        targets = object_names or self._objects
        lines = []
        for obj_name in targets:
            md = self.get_object_metadata(obj_name)
            if not md:
                continue
            lines.append(f"\n=== {obj_name} ===")
            lines.append(f"Label: {md.get('label', obj_name)}")
            lines.append("Queryable Fields:")
            for field in md.get("fields", []):
                ref_info = ""
                if field.get("referenceTo"):
                    ref_info = f" -> {', '.join(field['referenceTo'])}"
                rel_info = ""
                if field.get("relationshipName"):
                    rel_info = f" (relationship: {field['relationshipName']})"
                lines.append(
                    f"  - {field['name']} ({field['type']}){ref_info}{rel_info}"
                )
        return "\n".join(lines)

    def refresh_cache(self, object_name: str = None):
        """Force-refresh cache for one or all objects."""
        targets = [object_name] if object_name else self._objects
        for obj in targets:
            metadata = self._fetch_metadata(obj)
            if metadata:
                with self._lock:
                    self._cache[obj] = metadata
                    self._timestamps[obj] = time.time()
                self._save_to_disk(obj, metadata)
        print(f"🔄 Cache refreshed for: {targets}")

    def warm_cache(self):
        """Pre-populate cache for all configured objects on startup."""
        print("🔥 Warming metadata cache...")
        for obj in self._objects:
            md = self.get_object_metadata(obj)
            status = "✅" if md else "❌"
            field_count = len(md.get("fields", [])) if md else 0
            print(f"  {status} {obj}: {field_count} queryable fields")
        print("🔥 Cache warming complete")

    def get_cache_status(self) -> Dict[str, Any]:
        """Returns current cache status for all objects."""
        status = {}
        for obj in self._objects:
            with self._lock:
                is_cached = obj in self._cache and self._is_cache_valid(obj)
                ts = self._timestamps.get(obj)
            status[obj] = {
                "cached": is_cached,
                "field_count": len(self._cache.get(obj, {}).get("fields", [])),
                "last_refresh": datetime.fromtimestamp(ts).isoformat() if ts else None,
                "ttl_hours": self._ttl_hours,
                "expires_at": (
                    datetime.fromtimestamp(ts + self._ttl_hours * 3600).isoformat()
                    if ts
                    else None
                ),
            }
        return {
            "objects": status,
            "cache_dir": self._cache_dir,
            "ttl_hours": self._ttl_hours,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_cache_valid(self, object_name: str) -> bool:
        """Check if an in-memory cache entry is still within TTL."""
        if object_name not in self._cache:
            return False
        ts = self._timestamps.get(object_name, 0)
        age_hours = (time.time() - ts) / 3600
        return age_hours < self._ttl_hours

    def _fetch_metadata(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Fetch object metadata from Salesforce via describe() API."""
        from app.services.salesforce_service import salesforce_service

        if not salesforce_service.sf:
            print(f"⚠️ Salesforce not connected — cannot describe {object_name}")
            return None

        try:
            print(f"  🔍 Fetching describe() for {object_name}...")
            sf_object = getattr(salesforce_service.sf, object_name)
            describe_result = sf_object.describe()

            # Extract and filter fields
            fields = []
            relationships = []
            for field in describe_result.get("fields", []):
                # Skip non-queryable and compound fields
                if not field.get("name"):
                    continue

                field_info = {
                    "name": field["name"],
                    "label": field.get("label", field["name"]),
                    "type": field.get("type", "string"),
                    "length": field.get("length", 0),
                    "referenceTo": field.get("referenceTo", []),
                    "relationshipName": field.get("relationshipName"),
                    "isFilterable": field.get("filterable", False),
                    "isCreateable": field.get("createable", False),
                    "isUpdateable": field.get("updateable", False),
                    "isNillable": field.get("nillable", True),
                    "picklistValues": [
                        {"value": pv.get("value"), "label": pv.get("label")}
                        for pv in field.get("picklistValues", [])
                        if pv.get("active", True)
                    ] if field.get("type") in ("picklist", "multipicklist") else [],
                }

                fields.append(field_info)

                # Track relationship fields separately
                if field.get("referenceTo") and field.get("relationshipName"):
                    relationships.append({
                        "fieldName": field["name"],
                        "relationshipName": field["relationshipName"],
                        "referenceTo": field["referenceTo"],
                        "type": field.get("type"),
                    })

            metadata = {
                "object_name": object_name,
                "label": describe_result.get("label", object_name),
                "key_prefix": describe_result.get("keyPrefix"),
                "fields": fields,
                "relationships": relationships,
                "field_count": len(fields),
                "fetched_at": datetime.utcnow().isoformat(),
            }

            print(f"  ✅ {object_name}: {len(fields)} fields, {len(relationships)} relationships")
            return metadata

        except Exception as e:
            print(f"  ❌ Error describing {object_name}: {e}")
            return None

    def _save_to_disk(self, object_name: str, metadata: Dict[str, Any]):
        """Persist metadata to a JSON file on disk."""
        try:
            filepath = os.path.join(self._cache_dir, f"{object_name}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)
        except Exception as e:
            print(f"  ⚠️ Error saving cache for {object_name}: {e}")

    def _load_from_disk(self):
        """Load cached metadata from disk on startup."""
        if not os.path.exists(self._cache_dir):
            return

        for filename in os.listdir(self._cache_dir):
            if not filename.endswith(".json"):
                continue
            object_name = filename.replace(".json", "")
            filepath = os.path.join(self._cache_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                # Check if disk cache is still valid
                fetched_at = metadata.get("fetched_at")
                if fetched_at:
                    fetched_time = datetime.fromisoformat(fetched_at)
                    age_hours = (datetime.utcnow() - fetched_time).total_seconds() / 3600
                    if age_hours < self._ttl_hours:
                        self._cache[object_name] = metadata
                        self._timestamps[object_name] = fetched_time.timestamp()
                        print(f"  📁 Loaded {object_name} from disk cache ({len(metadata.get('fields', []))} fields)")
                    else:
                        print(f"  ⏰ Disk cache for {object_name} expired ({age_hours:.1f}h > {self._ttl_hours}h)")
            except Exception as e:
                print(f"  ⚠️ Error loading cache for {object_name}: {e}")


# Singleton instance
metadata_cache = MetadataCache()
