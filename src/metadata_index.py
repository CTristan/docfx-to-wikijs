from typing import Dict, List, Optional, Any

class MetadataIndex:
    def __init__(self, uid_to_item: Dict[str, Any]):
        self.uid_to_item = uid_to_item

    def get_base_class(self, uid: str) -> Optional[str]:
        """Returns the UID of the immediate base class."""
        item = self.uid_to_item.get(uid)
        if not item:
            return None
        
        # ItemInfo uses .inheritance list
        inheritance = getattr(item, "inheritance", [])
        if inheritance:
             # DocFX usually lists from root to immediate base.
             return inheritance[-1]
        return None

    def get_interfaces(self, uid: str) -> List[str]:
        """Returns list of UIDs of implemented interfaces."""
        item = self.uid_to_item.get(uid)
        if not item:
            return []
        return getattr(item, "implements", []) or []
