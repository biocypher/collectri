from functools import lru_cache
import hashlib
from enum import Enum, auto
from typing import Optional
import pandas as pd
from biocypher._logger import logger
from biocypher._create import BioCypherNode, BioCypherEdge

logger.debug(f"Loading module {__name__}.")


class CollectriAdapterNodeType(Enum):
    """
    Define types of nodes the adapter can provide.
    """

    GENE = auto()
    TRANSCRIPTION_FACTOR = auto()


class CollectriAdapterGeneField(Enum):
    """
    Define possible fields the adapter can provide for genes.
    """

    GENE_SYMBOL = "symbol"


class CollectriAdapterTranscriptionFactorField(Enum):
    """
    Define possible fields the adapter can provide for TFs.
    """

    GENE_SYMBOL = "symbol"
    CATEGORY = "TF.category"


class CollectriAdapterEdgeType(Enum):
    """
    Enum for the types of the protein adapter.
    """

    TRANSCRIPTIONAL_REGULATION = "regulates"


class CollectriAdapterTranscriptionalRegulationEdgeField(Enum):
    """
    Define possible fields the adapter can provide for protein-protein edges.
    """

    WEIGHT = "weight"
    RESOURCES = "resources"
    REFERENCES = "PMID"
    SIGN_DECISION = "sign.decision"


class CollectriAdapter:
    """
    Example BioCypher adapter. Generates nodes and edges for creating a
    knowledge graph.

    Args:
        node_types: List of node types to include in the result.
        node_fields: List of node fields to include in the result.
        edge_types: List of edge types to include in the result.
        edge_fields: List of edge fields to include in the result.
    """

    def __init__(
        self,
        file_path: str,
        node_types: Optional[list] = None,
        node_fields: Optional[list] = None,
        edge_types: Optional[list] = None,
        edge_fields: Optional[list] = None,
    ):
        self.file_path = file_path
        self._set_types_and_fields(
            node_types,
            node_fields,
            edge_types,
            edge_fields,
        )
        self._preprocess_data()

    def _preprocess_data(self):
        """
        Load the data from the given CSV and extract genes, transcription
        factors, and relationships.
        """
        logger.info("Preprocessing data.")

        # load data
        self.data = pd.read_csv(self.file_path)

        # extract genes (unique entities of `target` column)
        self.genes = self.data["target"].unique()

        # extract transcription factors (unique entities of `source` column and
        # the `TF.category` column)
        self.tf_df = self.data[["source", "TF.category"]].drop_duplicates()

    def get_nodes(self):
        """

        Returns a generator of BioCypher node objects for node types specified
        in the adapter constructor.

        Returns:
            Generator of BioCypher node objects.

        """

        logger.info("Generating nodes.")

        for node_id in self.genes:
            yield BioCypherNode(
                node_id=self._prefix(node_id),
                node_label="gene",
                preferred_id="hgnc.symbol",
                properties={
                    "name": node_id,
                },
            )

        for _, row in self.tf_df.iterrows():
            node_id = row["source"]
            category = row["TF.category"]
            properties = {
                "name": node_id,
            }
            properties["category"] = (
                "DNA-binding"
                if category == "dbTF"
                else (
                    "co-regulatory"
                    if category == "coTF"
                    else "general initiation" if category == "GTF" else None
                )
            )

            yield BioCypherNode(
                node_id=self._prefix(node_id),
                preferred_id="hgnc.symbol",
                node_label="transcription factor",
                properties=properties,
            )

    def get_edges(self):
        """

        Returns a generator of BioCypher edge objects (optionally
        BioCypherRelAsNode) for edge types specified in the adapter constructor.

        """

        logger.info("Generating edges.")

        # one row of the dataframe represents one edge
        for _, row in self.data.iterrows():
            # extract source and target
            source_id = row["source"]
            target_id = row["target"]

            # extract edge properties
            properties = {}

            if (
                CollectriAdapterTranscriptionalRegulationEdgeField.WEIGHT
                in self.edge_fields
            ):
                properties["activation_or_inhibition"] = (
                    "activation" if row["weight"] > 0 else "inhibition"
                )

            if (
                CollectriAdapterTranscriptionalRegulationEdgeField.RESOURCES
                in self.edge_fields
            ):
                properties["resources"] = row["resources"]

            if (
                CollectriAdapterTranscriptionalRegulationEdgeField.REFERENCES
                in self.edge_fields
            ):
                properties["references"] = row["PMID"]

            if (
                CollectriAdapterTranscriptionalRegulationEdgeField.SIGN_DECISION
                in self.edge_fields
            ):
                properties["sign_decision"] = row["sign.decision"]

            # generate relationship id
            md5 = hashlib.md5(
                "".join(
                    [str(source_id), str(target_id)]
                    + [str(prop) for prop in properties.values()]
                ).encode("utf-8")
            ).hexdigest()

            # generate edge
            yield BioCypherEdge(
                relationship_id=md5,
                source_id=self._prefix(source_id),
                target_id=self._prefix(target_id),
                relationship_label="transcriptional regulation",
                properties=properties,
            )

    def _set_types_and_fields(
        self,
        node_types,
        node_fields,
        edge_types,
        edge_fields,
    ):
        if node_types:
            self.node_types = node_types
        else:
            self.node_types = [type for type in CollectriAdapterNodeType]

        if node_fields:
            self.node_fields = node_fields
        else:
            self.node_fields = [
                field for field in CollectriAdapterTranscriptionFactorField
            ]

        if edge_types:
            self.edge_types = edge_types
        else:
            self.edge_types = [type for type in CollectriAdapterEdgeType]

        if edge_fields:
            self.edge_fields = edge_fields
        else:
            self.edge_fields = [
                field for field in CollectriAdapterTranscriptionalRegulationEdgeField
            ]

    @lru_cache(maxsize=None)
    def _prefix(self, string):
        return f"hgnc.symbol:{string}"
