# Path: components/qname_utils.py
"""
QName Utilities

Parse and manipulate QNames (qualified names).

QName format: namespace:localName
Examples: us-gaap:Revenue, ifrs:Assets
"""

from dataclasses import dataclass


@dataclass
class QName:
    """
    Qualified name representation.
    
    Attributes:
        namespace: Namespace prefix
        local_name: Local name
        full_name: Full QName (namespace:localName)
    """
    namespace: str
    local_name: str
    
    @property
    def full_name(self) -> str:
        """Get full QName."""
        if self.namespace:
            return f"{self.namespace}:{self.local_name}"
        return self.local_name
    
    def __str__(self) -> str:
        """String representation."""
        return self.full_name


class QNameUtils:
    """
    QName parsing and manipulation utilities.
    
    Example:
        # Parse QName
        qname = QNameUtils.parse('us-gaap:Revenue')
        print(qname.namespace)   # 'us-gaap'
        print(qname.local_name)  # 'Revenue'
        
        # Compare QNames
        match = QNameUtils.local_names_match('us-gaap:Revenue', 'ifrs:Revenue')
    """
    
    @staticmethod
    def parse(qname_str: str) -> QName:
        """
        Parse QName string - handles MULTIPLE formats.
        
        Supported formats:
        1. Clark notation: {http://fasb.org/us-gaap/2024}Assets
        2. Prefix format: us-gaap:Assets  
        3. Underscore format: us-gaap_Assets
        4. Simple name: Assets
        
        Args:
            qname_str: QName in any format
            
        Returns:
            QName object
        """
        if not qname_str:
            return QName(namespace='', local_name='')
        
        qname_str = str(qname_str).strip()
        
        # Format 1: Clark notation {namespace}localName
        if qname_str.startswith('{'):
            try:
                # Split on }
                parts = qname_str.split('}', 1)
                if len(parts) == 2:
                    namespace = parts[0][1:]  # Remove leading {
                    local_name = parts[1]
                    return QName(namespace=namespace, local_name=local_name)
            except:
                pass
        
        # Format 2: Prefix format namespace:localName
        if ':' in qname_str:
            namespace, local_name = qname_str.split(':', 1)
            return QName(namespace=namespace, local_name=local_name)
        
        # Format 3: Underscore format namespace_localName (try to split on last underscore)
        if '_' in qname_str:
            # Check if this looks like a namespace_LocalName pattern
            # (LocalName typically starts with uppercase)
            parts = qname_str.rsplit('_', 1)
            if len(parts) == 2 and parts[1] and parts[1][0].isupper():
                return QName(namespace=parts[0], local_name=parts[1])
        
        # Format 4: Simple name (no namespace)
        return QName(namespace='', local_name=qname_str)
    
    @staticmethod
    def get_namespace(qname_str: str) -> str:
        """Extract namespace from QName string."""
        qname = QNameUtils.parse(qname_str)
        return qname.namespace
    
    @staticmethod
    def get_local_name(qname_str: str) -> str:
        """Extract local name from QName string."""
        qname = QNameUtils.parse(qname_str)
        return qname.local_name
    
    @staticmethod
    def local_names_match(qname1_str: str, qname2_str: str) -> bool:
        """
        Check if local names match (ignoring namespaces).
        
        Args:
            qname1_str: First QName string
            qname2_str: Second QName string
            
        Returns:
            True if local names match
        """
        qname1 = QNameUtils.parse(qname1_str)
        qname2 = QNameUtils.parse(qname2_str)
        return qname1.local_name == qname2.local_name
    
    @staticmethod
    def replace_namespace(qname_str: str, new_namespace: str) -> str:
        """
        Replace namespace in QName.
        
        Args:
            qname_str: Original QName string
            new_namespace: New namespace
            
        Returns:
            QName with new namespace
        """
        qname = QNameUtils.parse(qname_str)
        return f"{new_namespace}:{qname.local_name}"


__all__ = ['QName', 'QNameUtils']