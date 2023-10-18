# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Common spinup to be used by different subsequent simulations

# %load_ext autoreload

# +
import numpy as np
import xarray as xr
import argparse

from bgc_md2.notebook_helpers import write_to_logfile
from CompartmentalSystems.discrete_model_run import DiscreteModelRun as DMR
from LAPM.discrete_linear_autonomous_pool_model import DiscreteLinearAutonomousPoolModel as DLAPM

from ACGCA import utils
from ACGCA.__init__ import DATA_PATH, Q_
from ACGCA.simulation_parameters import stand_params_library
from ACGCA.simulation import utils as sim_utils
from ACGCA.soil.dead_wood_classes.C_model import SoilCDeadWoodClasses
from ACGCA.wood_products.simple_wood_product_model import SimpleWoodProductModel
from ACGCA.management.library import species_setting_from_sim_profile

from ACGCA.productivity.stand import Stand
from ACGCA.simulation.library import prepare_forcing

from ACGCA.simulation.recorded_simulation import RecordedSimulation
from ACGCA.alloc.ACGCA_marklund_tree_params import species_params

# %autoreload 2
# -

all_sims_path = DATA_PATH.joinpath("simulations")
all_sims_path.mkdir(exist_ok=True)

# ### Custom species parameters?

# +
# #%tb

try:
    parser = argparse.ArgumentParser()
    parser.add_argument("pre_spinup_date", type=str)

    parser.add_argument("common_spinup_species", type=str) # continuous-cover (age-distributed) spinup
    parser.add_argument("common_spinup_length", type=int)
    parser.add_argument("common_spinup_N", type=int)
 
    parser.add_argument("sim_date", type=str)
    parser.add_argument("sim_name", type=str)

    args = parser.parse_args()

    pre_spinup_date = args.pre_spinup_date
    common_spinup_species = args.common_spinup_species
    common_spinup_length = args.common_spinup_length
    common_spinup_N = args.common_spinup_N
    sim_date = args.sim_date
    sim_name = args.sim_name
    print("Simulation settings from command line")
except SystemExit:
    print("Standard simulation settings")

    pre_spinup_date = "2023-06-22"

    # "common" means used by all simulations
    common_spinup_species = "pine"
    common_spinup_length = 8 * 20
    common_spinup_N = 2_000

    sim_date = "2023-06-23"
#    sim_name = "mixed-aged_pine_long"
#    sim_name = "even-aged_pine_long"
#    sim_name = "even-aged_spruce_long"
#    sim_name = "even-aged_mixed_long"
    sim_name = f"DWC_common_spinup_{common_spinup_species}_clear_cut"
    
sim_dict = {
    "pre_spinup_date": pre_spinup_date,
    
    "common_spinup_species": common_spinup_species,
    "common_spinup_length": common_spinup_length,
    "common_spinup_N": common_spinup_N,

    "sim_date": sim_date,
    "sim_name": sim_name,
}

print(sim_dict)
# -

# ## Set up forcing and simulation length

# +
# simulation data


# start `spinup_length` years earlier so as to have the true start again at 2000
nr_copies = sim_dict["common_spinup_length"] // 20
forcing = prepare_forcing(nr_copies=nr_copies, year_offset=-sim_dict["common_spinup_length"])

sim_cohort_name = ""
sim_cohort_path = all_sims_path.joinpath(sim_cohort_name)
sim_cohort_path = sim_cohort_path.joinpath(f"{sim_dict['sim_date']}")

sim_cohort_path.mkdir(exist_ok=True)
print(sim_cohort_path)
# -

# ## Load pre-spinup data: soil and wood product stocks and age structure

# +
spinups_path = DATA_PATH.joinpath("pre_spinups").joinpath(sim_dict["pre_spinup_date"])

light_model = "Zhao" # Zhao or Spitters

pre_spinup_species = "pine"
#pre_spinup_name = f"basic_{light_model}_{pre_spinup_species}_2nd_round"
pre_spinup_name = f"DWC_{light_model}_{pre_spinup_species}_2nd_round"
dmr_path = spinups_path.joinpath(pre_spinup_name + ".dmr_eq")

# load fake equilibrium dmr
dmr_eq = DLAPM.load_from_file(dmr_path)

# initialize soil and wood product models with spinup stocks
soil_model = SoilCDeadWoodClasses(initial_stocks=Q_(dmr_eq.xss[dmr_eq.soil_pool_nrs], "gC/m^2"))
wood_product_model = SimpleWoodProductModel(initial_stocks=Q_(dmr_eq.xss[dmr_eq.wood_product_pool_nrs], "gC/m^2"))

stand_params = stand_params_library["default"]
stand_params["soil_model"] = soil_model
stand_params["wood_product_model"] = wood_product_model
#stand_params["wood_product_model_interface"] = "default"

print(dmr_path)
# -


sim_name = sim_dict["sim_name"]
sim_name

# +
management_strategy = [
    ("StandAge3", "Plant"),
    ("PCT", "T0.75"), # will be reactivated automatically after a clear cut
    ("SBA25-80-160", "ThinStandToSBA18"),
    ("StandAge79", "CutWait3AndReplant"),   
]

cc_management_strategies = [
    [
        ("StandAge3", "Plant"),
        ("StandAge99", "CutWait3AndReplant"),
        ("StandAge19", "CutWait3AndReplant"),
    ],
    [
        ("StandAge3", "Plant"),
        ("StandAge119", "CutWait3AndReplant"),
        ("StandAge39", "CutWait3AndReplant"),
    ],
    [
        ("StandAge3", "Plant"),
        ("StandAge139", "CutWait3AndReplant"),
        ("StandAge59", "CutWait3AndReplant"),
    ],
    [
        ("StandAge3", "Plant"),
#        ("StandAge159", "CutWait3AndReplant"),
        ("StandAge79", "CutWait3AndReplant"),
    ],
]


# +
species = sim_dict["common_spinup_species"]
N = sim_dict["common_spinup_N"]
if species in ["pine", "spruce"]:
    sim_profile =  [
        (species, 1.0, N / 10_000 / 4, management_strategy, "waiting"),
        (species, 1.2, N / 10_000 / 4, management_strategy, "waiting"),
        (species, 1.4, N / 10_000 / 4, management_strategy, "waiting"),
        (species, 1.6, N / 10_000 / 4, management_strategy, "waiting"),
    ]

elif species == "mixed":
    sim_profile =  [
        ("pine", 1.2, N / 10_000 / 4, management_strategy, "waiting"),
        ("pine", 1.4, N / 10_000 / 4, management_strategy, "waiting"),
        ("spruce", 1.2, N / 10_000 / 4, management_strategy, "waiting"),
        ("spruce", 1.4, N / 10_000 / 4, management_strategy, "waiting"),
    ]
    
elif species in ["cc_pine", "cc_spruce"]:
    species_ = species[3:]

    sim_profile = [
        (species_, 1.0, N / 10_000.0 / 4, management_strategy, "waiting")
        for management_strategy in cc_management_strategies
    ]
    
else:
    raise ValueError(f"Unknown common spinup species: {species}")


# +
emergency_action_str, emergency_direction, emergency_stand_action_str = "Die", "below", ""
#emergency_action_str, emergency_direction = "Thin", "below"
#emergency_action_str, emergency_direction = "CutWait3AndReplant", "above"

emergency_q = 0.75 # remaining fraction after emergency thinning (in case it is asked for)

species_setting = species_setting_from_sim_profile(sim_profile)

logfile_path = sim_cohort_path.joinpath(sim_name + ".log")
print(f"log file: {logfile_path}")

# +
# %%time
  
stand = Stand.create_empty(stand_params)
stand.add_trees_from_setting(species_setting, custom_species_params=species_params)

print(stand)
# -

# ## Run common spinup

recorded_simulation = RecordedSimulation.from_simulation_run(
    sim_name,
    logfile_path,
    sim_profile,
    light_model,
#    "Spitters",
    forcing,
#    custom_species_params,
    species_params,
    stand,
#    final_felling,
    emergency_action_str,
    emergency_direction,
    emergency_q, # fraction to keep
    emergency_stand_action_str, # in case of emergency, also do this
)

# ### Save common spinup dataset and simulation

filepath = sim_cohort_path.joinpath(sim_name + ".dmp")
recorded_simulation.save_to_file(filepath)
print(filepath)

# ## Load recorded simulation and all the objects

filepath = sim_cohort_path.joinpath(sim_name + ".dmp")
recorded_simulation = RecordedSimulation.from_file(filepath)

