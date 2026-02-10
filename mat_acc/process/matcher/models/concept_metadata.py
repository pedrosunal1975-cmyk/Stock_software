# Path: mat_acc/process/matcher/models/concept_metadata.py
"""
Concept Metadata Models

Models for storing concept attributes used during matching.
The ConceptIndex provides fast lookup during candidate filtering.
"""

from typing import Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ConceptMetadata:
    """
    Metadata for a single XBRL concept.

    Contains all attributes that can be matched against component
    definition rules.

    Attributes:
        qname: Full qualified name (e.g., "us-gaap:AssetsCurrent")
        local_name: Local part of QName (e.g., "AssetsCurrent")
        namespace: Namespace URI
        prefix: Namespace prefix (e.g., "us-gaap")
        labels: All labels by type (standard, terse, verbose, etc.)
        definition: Definition text from taxonomy
        balance_type: Debit, credit, or none
        period_type: Instant or duration
        is_abstract: Whether concept is abstract
        references: Accounting standard references
        presentation_parent: Parent in presentation hierarchy
        presentation_level: Depth in presentation hierarchy
        presentation_order: Order among siblings
        calculation_children: Children in calculation linkbase
        calculation_parents: Parents in calculation linkbase
    """
    # Identity
    qname: str
    local_name: str
    namespace: Optional[str] = None
    prefix: Optional[str] = None

    # Labels (label_type -> label_text)
    labels: dict[str, str] = field(default_factory=dict)

    # Definition
    definition: Optional[str] = None

    # Characteristics
    balance_type: Optional[str] = None  # "debit", "credit", or None
    period_type: Optional[str] = None   # "instant" or "duration"
    is_abstract: bool = False
    data_type: Optional[str] = None

    # References (list of {standard, section, paragraph})
    references: list[dict[str, str]] = field(default_factory=list)

    # Presentation hierarchy
    presentation_parent: Optional[str] = None
    presentation_level: int = 0
    presentation_order: float = 0.0
    presentation_siblings: list[str] = field(default_factory=list)

    # Calculation relationships
    calculation_children: list[dict] = field(default_factory=list)
    # Each child: {qname, weight, order}
    calculation_parents: list[dict] = field(default_factory=list)
    # Each parent: {qname, weight}

    def get_label(self, label_type: str = 'standard') -> Optional[str]:
        """Get label of specified type."""
        return self.labels.get(label_type)

    def get_all_labels(self) -> list[str]:
        """Get all label texts."""
        return list(self.labels.values())

    def has_reference(self, standard: str, section: str) -> bool:
        """Check if concept has a specific reference."""
        for ref in self.references:
            if ref.get('standard') == standard and section in ref.get('section', ''):
                return True
        return False

    def get_calculation_child_qnames(self) -> list[str]:
        """Get QNames of calculation children."""
        return [child['qname'] for child in self.calculation_children]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'qname': self.qname,
            'local_name': self.local_name,
            'namespace': self.namespace,
            'prefix': self.prefix,
            'labels': self.labels,
            'definition': self.definition,
            'balance_type': self.balance_type,
            'period_type': self.period_type,
            'is_abstract': self.is_abstract,
            'data_type': self.data_type,
            'references': self.references,
            'presentation_parent': self.presentation_parent,
            'presentation_level': self.presentation_level,
            'presentation_order': self.presentation_order,
            'calculation_children': self.calculation_children,
            'calculation_parents': self.calculation_parents,
        }


class ConceptIndex:
    """
    Index for fast concept lookup during matching.

    Pre-indexes concepts by various attributes to enable fast
    candidate filtering before full rule evaluation.

    Indexes:
        - by_local_name: Local name -> concepts
        - by_label_word: Word in label -> concepts
        - by_balance_type: Balance type -> concepts
        - by_period_type: Period type -> concepts
        - by_parent: Parent concept -> child concepts
    """

    def __init__(self):
        """Initialize empty index."""
        self._concepts: dict[str, ConceptMetadata] = {}

        # Indexes for fast lookup
        self._by_local_name: dict[str, list[str]] = defaultdict(list)
        self._by_label_word: dict[str, set[str]] = defaultdict(set)
        self._by_balance_type: dict[str, list[str]] = defaultdict(list)
        self._by_period_type: dict[str, list[str]] = defaultdict(list)
        self._by_parent: dict[str, list[str]] = defaultdict(list)
        self._by_level: dict[int, list[str]] = defaultdict(list)

    def add_concept(self, concept: ConceptMetadata) -> None:
        """
        Add a concept to the index.

        Args:
            concept: Concept metadata to index
        """
        qname = concept.qname
        self._concepts[qname] = concept

        # Index by local name (lowercase for case-insensitive lookup)
        local_lower = concept.local_name.lower()
        self._by_local_name[local_lower].append(qname)

        # Index by words in labels
        for label in concept.get_all_labels():
            words = self._tokenize(label)
            for word in words:
                self._by_label_word[word].add(qname)

        # Index by balance type
        if concept.balance_type:
            self._by_balance_type[concept.balance_type].append(qname)

        # Index by period type
        if concept.period_type:
            self._by_period_type[concept.period_type].append(qname)

        # Index by parent
        if concept.presentation_parent:
            self._by_parent[concept.presentation_parent].append(qname)

        # Index by level
        self._by_level[concept.presentation_level].append(qname)

    def get_concept(self, qname: str) -> Optional[ConceptMetadata]:
        """Get concept by QName."""
        return self._concepts.get(qname)

    def get_all_concepts(self) -> list[ConceptMetadata]:
        """Get all indexed concepts."""
        return list(self._concepts.values())

    def find_by_local_name(self, pattern: str) -> list[str]:
        """
        Find concepts by local name pattern.

        Args:
            pattern: Pattern with optional wildcards (*)

        Returns:
            List of matching QNames
        """
        pattern_lower = pattern.lower().replace('*', '')
        matches = []

        for local_name, qnames in self._by_local_name.items():
            if pattern.startswith('*') and pattern.endswith('*'):
                if pattern_lower in local_name:
                    matches.extend(qnames)
            elif pattern.startswith('*'):
                if local_name.endswith(pattern_lower):
                    matches.extend(qnames)
            elif pattern.endswith('*'):
                if local_name.startswith(pattern_lower):
                    matches.extend(qnames)
            else:
                if local_name == pattern_lower:
                    matches.extend(qnames)

        return matches

    def find_by_label_words(self, words: list[str]) -> set[str]:
        """
        Find concepts containing all specified words in labels.

        Args:
            words: Words that must appear in labels

        Returns:
            Set of matching QNames
        """
        if not words:
            return set()

        words_lower = [w.lower() for w in words]

        # Start with concepts matching first word
        result = self._by_label_word.get(words_lower[0], set()).copy()

        # Intersect with concepts matching other words
        for word in words_lower[1:]:
            result &= self._by_label_word.get(word, set())

        return result

    def find_by_characteristics(
        self,
        balance_type: Optional[str] = None,
        period_type: Optional[str] = None,
        exclude_abstract: bool = True
    ) -> set[str]:
        """
        Find concepts matching characteristics.

        Args:
            balance_type: Required balance type
            period_type: Required period type
            exclude_abstract: Whether to exclude abstract concepts

        Returns:
            Set of matching QNames
        """
        # Start with all concepts
        result = set(self._concepts.keys())

        # Filter by balance type
        if balance_type:
            balance_concepts = set(self._by_balance_type.get(balance_type, []))
            result &= balance_concepts

        # Filter by period type
        if period_type:
            period_concepts = set(self._by_period_type.get(period_type, []))
            result &= period_concepts

        # Filter out abstracts
        if exclude_abstract:
            result = {
                qname for qname in result
                if not self._concepts[qname].is_abstract
            }

        return result

    def find_children_of(self, parent_qname: str) -> list[str]:
        """Find concepts that are children of the given parent."""
        return self._by_parent.get(parent_qname, [])

    def find_at_level(self, level: int) -> list[str]:
        """Find concepts at a specific hierarchy level."""
        return self._by_level.get(level, [])

    def get_candidates(
        self,
        label_patterns: list[str],
        local_name_patterns: Optional[list[str]] = None,
        balance_type: Optional[str] = None,
        period_type: Optional[str] = None,
        exclude_abstract: bool = True,
        max_candidates: int = 100
    ) -> list[str]:
        """
        Get candidate concepts for matching.

        Uses multiple indexes to quickly find likely candidates
        before full rule evaluation.

        Characteristic filtering is permissive:
        - Concepts with matching characteristics are included
        - Concepts with None/unknown characteristics are included
        - Only concepts with WRONG characteristics are excluded

        Args:
            label_patterns: Patterns to search for in labels
            local_name_patterns: Patterns to search for in local names
            balance_type: Preferred balance type (None = no preference)
            period_type: Preferred period type (None = no preference)
            exclude_abstract: Whether to exclude abstract concepts
            max_candidates: Maximum candidates to return

        Returns:
            List of candidate QNames
        """
        # Extract words from patterns
        all_words = set()
        for pattern in label_patterns:
            words = self._tokenize(pattern)
            all_words.update(words)

        # Find by label words (union of matches for each word)
        label_matches = set()
        for word in all_words:
            label_matches.update(self._by_label_word.get(word, set()))

        # Also search by local name patterns (catches company extensions)
        if local_name_patterns:
            for pattern in local_name_patterns:
                label_matches.update(
                    self.find_by_local_name(f"*{pattern}*")
                )

        # If still no matches, try label patterns as local names
        if not label_matches:
            for pattern in label_patterns:
                label_matches.update(self.find_by_local_name(f"*{pattern}*"))

        # Filter by characteristics
        if label_matches:
            candidates = label_matches
        else:
            candidates = set(self._concepts.keys())

        # Apply PERMISSIVE characteristic filters
        # Include concepts with matching type OR unknown (None) type
        # Only exclude concepts with WRONG type
        if balance_type:
            filtered = set()
            for qname in candidates:
                concept = self._concepts[qname]
                # Include if: matches OR is unknown (None)
                if concept.balance_type is None or concept.balance_type == balance_type:
                    filtered.add(qname)
            candidates = filtered

        if period_type:
            filtered = set()
            for qname in candidates:
                concept = self._concepts[qname]
                # Include if: matches OR is unknown (None)
                if concept.period_type is None or concept.period_type == period_type:
                    filtered.add(qname)
            candidates = filtered

        if exclude_abstract:
            candidates = {
                qname for qname in candidates
                if not self._concepts[qname].is_abstract
            }

        # Limit and return
        return list(candidates)[:max_candidates]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into lowercase words."""
        # Remove punctuation and split
        import re
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        # Filter short words
        return [w for w in words if len(w) >= 3]

    def __len__(self) -> int:
        """Return number of indexed concepts."""
        return len(self._concepts)

    def __contains__(self, qname: str) -> bool:
        """Check if concept is indexed."""
        return qname in self._concepts


__all__ = [
    'ConceptMetadata',
    'ConceptIndex',
]
