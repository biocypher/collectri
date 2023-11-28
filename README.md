# BioCypher adapter for the CollecTRI dataset

This repository contains the code for the BioCypher adapter for the CollecTRI
dataset. The adapter is a Python module that converts the CollecTRI dataset into
the BioCypher format. It also serves as a tutorial for end-to-end knowledge
graph construction using BioCypher.

## Process

1. Download and cache the resource

2. Run BioCypher to create knowledge graph

3. Deploy knowledge graph and web frontend

## Tutorial

1. Create repository: using the template repository is the easiest way to get
started. The [template
repository](https://github.com/biocypher/project-template) contains the basic
structure of a BioCypher adapter. Clone the template repository and rename it
and the adapter to your project's name. Also adjust the `pyproject.toml` file to
reflect your project's name and version.

2. Find the data: the CollecTRI dataset is available as a flat file at
https://rescued.omnipathdb.org/CollecTRI.csv. With this link, we can set up a
BioCypher `Resource` object to [download and cache the
data](https://biocypher.org/api.html#download-and-cache-functionality). We
implement this and all other steps of the build pipeline in the
`create_knowledge_graph.py` script. Check there for the full code.

```python
bc = BioCypher()
collectri = Resource(
    name="collectri",
    url_s="https://rescued.omnipathdb.org/CollecTRI.csv",
    lifetime=0,  # CollecTRI is a static resource
)
paths = bc.download(collectri)
```

3. Adjust the adapter based on the contents of the dataset. This is the most
labour-intensive step, as it involves systematising the dataset and mapping it
to a suitable ontology, as well as designing the ETL (extract-transform-load)
process in the adapter module. The CollecTRI dataset is comparatively simple,
which makes it a good example. You can find a detailed description of the
process [below](#adapter-design) ([adapter design](#adapter-design) and [ontolgy
mapping](#ontology-mapping)).

When building the adapter, it can be helpful to use the Pandas functionality of
BioCypher to preview the KG components. Using the `add()` and `to_df()` methods,
we can check whether the adapter is working as expected.

```python
bc.add(adapter.get_nodes())
bc.add(adapter.get_edges())
dfs = bc.to_df()
for name, df in dfs.items():
    print(name)
    print(df.head())
```

4. Run BioCypher to create the knowledge graph. This step is straightforward,
using the information provided by the mapping configuration and the process
provided by the adapter created in the previous step. For compatibility with the
Docker compose workflow, we use the `write_nodes()` and `write_edges()` methods
to generate CSV files for import into Neo4j, as well as the import call
statement and a summary of the build process.

```python
bc.write_nodes(adapter.get_nodes())
bc.write_edges(adapter.get_edges())

# Write admin import statement
bc.write_import_call()

# Print summary
bc.summary()
```

5. Run Docker compose to deploy the knowledge graph. Running the standard
`docker-compose.yaml` configuration will build the graph, import it into Neo4j,
and deploy a Neo4j instance to be accessed on https://localhost:7474. The graph
can then be browsed and queried.

```bash
docker compose up -d
```

You can also include the ChatGSE frontend in the deployment by running the
`docker-compose-chatgse.yaml` configuration. This will also deploy a ChatGSE
instance to be accessed on https://localhost:8501. In the `Knowledge Graph` tab,
you can use natural language queries to generate Cypher queries and run them on
the graph. For connecting, you need to change the Neo4j host IP from `localhost`
to `deploy`, which is the name of the Docker service running the Neo4j instance.

```bash
docker compose -f docker-compose-chatgse.yaml up -d
```

To stop the deployment, run

```bash
docker compose down --volumes
```

or

```bash
docker compose -f docker-compose-chatgse.yaml down --volumes
```

Removing the volumes is necessary to ensure a clean deployment when running
`docker compose up` again. Otherwise, the graph will contain duplicate nodes and
edges.

## Adapter design

We can look at the downloaded dataset (using the path from the previous step) to
get an idea of its contents:

```python
import pandas as pd
df = pd.read_csv(paths[0])
print(df.head())
#   source target  weight  ...                                          resources                                               PMID       sign.decision
# 0    MYC   TERT       1  ...  ExTRI;HTRI;TRRUST;TFactS;NTNU.Curated;Pavlidis...  10022128;10491298;10606235;10637317;10723141;1...                PMID
# 1   SPI1  BGLAP       1  ...                                              ExTRI                                           10022617  default activation
# 2    AP1    JUN       1  ...                          ExTRI;TRRUST;NTNU.Curated  10022869;10037172;10208431;10366004;11281649;1...                PMID
# 3  SMAD3    JUN       1  ...                   ExTRI;TRRUST;TFactS;NTNU.Curated                                  10022869;12374795                PMID
# 4  SMAD4    JUN       1  ...                   ExTRI;TRRUST;TFactS;NTNU.Curated                                  10022869;12374795                PMID
print(df.columns)
# Index(['source', 'target', 'weight', 'TF.category', 'resources', 'PMID',
#        'sign.decision'],
#       dtype='object')
```

We can then use this knowledge to design the adapater, i.e., the ETL process.
Briefly, the adapter extracts sources and targets, which are both genes, and
establishes relationships that embody the regulons. These relationships are
enriched by the curation information contained in the table.

We use Enums to define the types of nodes and edges and their properties. This
helps in organising the process and also allows the use of auto-completion in
downstream tasks. We have two node types, `gene` and `transcription factor`, and
one relationship type, `transcriptional regulation`. We also define the
properties of the nodes and edges, which are none for genes, `category` for
transcription factors, and `weight`, `resources`, `references`, and
`sign_decision` for the relationship. (Note that we rename some of the original
attributes to make them more intuitive, e.g., `PMID` to `references`, or
machine-compatible, e.g., `sign.decision` to `sign_decision`. This conversion is
handled by the adapter and needs to be reflected in our schema configuration.)

The adapter then uses the `pandas` library to read the dataset and extract the
relevant information. We use the `_preprocess_data()` method to load the
dataframe and extract unique genes and TFs. Since each row of the dataset is one
relationship, we can simply iterate over the rows to create the relationships
directly.

The last component the adapter needs is two public methods, `get_nodes()` and
`get_edges()`, which return generators of nodes and edges, respectively. These
methods are used in the build script (`create_knowledge_graph.py`) to create the
knowledge graph.

## Ontology mapping

<!-- TODO doc links -->

In addition, we use the information to create an [ontology
mapping](https://biocypher.org/tutorial-ontology.html#using-ontologies-plain-biolink)
in the `schema_config.yaml` file, which reflect the ontological grounding of the
data.  Since CollecTRI deals with transcriptional regulation in a gene-gene
context, we only need to define `gene` nodes and some regulatory interaction
between them.  For this simple case, we resort to the shallow default ontology,
[Biolink](https://bioportal.bioontology.org/ontologies/BIOLINK?p=classes&conceptid=root),
which already contains Gene entities and regulatory relationships. This also
means we do not need to specify the ontology in the `biocypher_config.yaml`
file, as Biolink is the default.

We use the existing entity type `gene`, and we extend the existing `pairwise
gene to gene association` relationship to `transcriptional regulation` using
[inheritance](https://biocypher.org/tutorial-ontology.html#model-extensions).
For clarity, we also introduce a `transcription factor` entity type, which
inherits from `gene`; this way, we can query for transcription factors
specifically while retaining the ability to query for all genes.

```yaml
gene:
    represented_as: node
    preferred_id: hgnc.symbol
    properties:
        name: str

transcription factor:
    is_a: gene
    represented_as: node
    preferred_id: hgnc.symbol
    properties:
        name: str
        category: str

transcriptional regulation:
    is_a: pairwise gene to gene interaction
    represented_as: edge
    source: transcription factor
    target: gene
    properties:
        weight: float
        resources: str
        references: str
        sign_decision: str
```

Note that, since we pass `BioCypherNode` and `BioCypherEdge` objects to the
BioCypher instance, which already include the correct labels of the ontology
classes we map to (`gene`, `transcription factor`, and `transcriptional
regulation`), we do not need to specify the `input_label` fields of each class.

We do, however, add some optional components to the schema configuration, mainly
to make interaction with the LLM framework BioChatter easier. For instance, we
provide explicit `properties` for each class, which are used to generate the
`schema_info.yaml` file, an extended schema configuration for BioChatter
integration. We also include the `name` property as a shortcut to the gene
symbol without added prefix (which usually is good practice to ensure uniqueness
of identifiers, in this case the `hgnc.symbol`). This way, we (and the LLM) can
use the `name` property to refer to genes by their symbol, e.g., `MYC` instead
of `hgnc.symbol:MYC`.