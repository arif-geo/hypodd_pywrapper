import hypodd_pywrapper.scripts.run_hypodd as run_hypodd
try:
    run_hypodd.prepare_inputs()
except Exception as e:
    print(f"Error: {e}")
