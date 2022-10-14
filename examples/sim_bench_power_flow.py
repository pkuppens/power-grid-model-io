# SPDX-FileCopyrightText: 2022 Contributors to the Power Grid Model IO project <dynamic.grid.calculation@alliander.com>
#
# SPDX-License-Identifier: MPL-2.0

import logging
from pathlib import Path

import structlog
from power_grid_model import PowerGridModel

from power_grid_model_io.converters.pgm_json_converter import PgmJsonConverter
from power_grid_model_io.converters.sim_bench_converter import SimBenchConverter

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

# Load source
simbenc_code = "1-complete_data-mixed-all-0-sw"
simbench_converter = SimBenchConverter(simbenc_code)

# Convert to PGM
input_data, extra_info = simbench_converter.load_input_data()

# Store the source data in JSON format
converter = PgmJsonConverter(destination_file=f"data/sim-bench/{simbenc_code}_input.json")
converter.save(data=input_data, extra_info=extra_info)

# Perform power flow calculation
grid = PowerGridModel(input_data=input_data)
output_data = grid.calculate_power_flow()

# Store the result data in JSON format
converter = PgmJsonConverter(destination_file=f"data/sim-bench/{simbenc_code}_output.json")
converter.save(data=output_data, extra_info=extra_info)
