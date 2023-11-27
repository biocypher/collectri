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
data](https://biocypher.org/api.html#download-and-cache-functionality).

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

4. Run BioCypher to create the knowledge graph. This step is straightforward,
using the information provided by the mapping configuration and the process
provided by the adapter created in the previous step.

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
downstream tasks.

## Ontology mapping

<!-- TODO doc links -->

In addition, we use the information to create an [ontology mapping]() in the
`schema_config.yaml` file, which reflect the ontological grounding of the data.
Since CollecTRI deals with transcriptional regulation in a gene-gene context, we
only need to define `gene` nodes and some regulatory interaction between them.
For this simple case, we resort to the shallow default ontology,
[Biolink](https://bioportal.bioontology.org/ontologies/BIOLINK?p=classes&conceptid=root),
which already contains Gene entities and regulatory relationships. This also
means we do not need to specify the ontology in the `biocypher_config.yaml`
file, as Biolink is the default.

We use the existing entity type `gene`, and we extend the existing `pairwise
gene to gene association` relationship to `transcriptional regulation` using
[inheritance](). For clarity, we also introduce a `transcription factor` entity
type, which inherits from `gene`; this way, we can query for transcription
factors specifically while retaining the ability to query for all genes.

```yaml
gene:
    represented_as: node
    preferred_id: uniprot
    input_label: gene

transcription factor:
    is_a: gene
    represented_as: node
    input_label: tf

transcriptional regulation:
    is_a: pairwise gene to gene association
    represented_as: edge
    source: transcription factor
    target: gene
    input_label: regulates
```