from biocypher import BioCypher, Resource
from collectri.adapters.collectri_adapter import CollectriAdapter

# ----------------------
# Setup: Should optional steps be run?
# ----------------------

RUN_OPTIONAL_STEPS = True

# ----------------------
# Step 1: Data download and cache
# ----------------------

bc = BioCypher()
collectri = Resource(
    name="collectri",
    url_s="https://rescued.omnipathdb.org/CollecTRI.csv",
    lifetime=0,  # CollecTRI is a static resource
)

paths = bc.download(collectri)

# ----------------------
# Optional: Inspect data
# ----------------------

if RUN_OPTIONAL_STEPS:
    import pandas as pd

    df = pd.read_csv(paths[0])
    print(df.head())
    print(df.columns)

# ----------------------
# Step 2: Load and configure adapter
# ----------------------

adapter = CollectriAdapter(paths[0])

# ----------------------
# Optional: For prototyping, we can use the Pandas functionality
# ----------------------

if RUN_OPTIONAL_STEPS:
    bc.add(adapter.get_nodes())
    bc.add(adapter.get_edges())
    dfs = bc.to_df()
    for name, df in dfs.items():
        print(name)
        print(df.head())

    bc = BioCypher()
    # Reset BioCypher, otherwise we would deduplicate all entities from previous
    # run. This is not needed if this optional step is skipped/removed.

# ----------------------
# Step 3: Write nodes and edges, import call, and summarise the run
# ----------------------

bc.write_nodes(adapter.get_nodes())
bc.write_edges(adapter.get_edges())

# TODO preferred_id is not reflected in the output

# Write admin import statement and schema information (for biochatter)
bc.write_import_call()
bc.write_schema_info(as_node=True)

# Print summary
bc.summary()
