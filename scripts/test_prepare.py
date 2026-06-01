import run_hypodd
try:
    run_hypodd.prepare_inputs()
except Exception as e:
    print(f"Error: {e}")
