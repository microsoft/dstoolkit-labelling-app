#!/bin/bash

export PYTHONPATH=${PYTHONPATH}:${PWD}

streamlit run webpage/main.py --server.port 8000 --server.address 0.0.0.0
