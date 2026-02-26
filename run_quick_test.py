import sys
import yaml
import pandas as pd

# Ensure src is on path
sys.path.append('src')

from fmea_generator import FMEAGenerator

with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

gen = FMEAGenerator(config)

sample = pd.DataFrame([
    {'Failure Mode':'engine overheats','Effect':'engine temperature high','Severity':7,'Occurrence':2,'Detection':5,'Rpn':70,'Action Priority':'High','Recommended Action':'A'},
    {'Failure Mode':'overheating engine','Effect':'engine temperature increased','Severity':8,'Occurrence':3,'Detection':4,'Rpn':96,'Action Priority':'Critical','Recommended Action':'B'},
    {'Failure Mode':'car got too hot','Effect':'vehicle overheated','Severity':6,'Occurrence':1,'Detection':5,'Rpn':30,'Action Priority':'Medium','Recommended Action':'C'},
    {'Failure Mode':'brakes failed','Effect':'braking loss','Severity':9,'Occurrence':2,'Detection':6,'Rpn':108,'Action Priority':'Critical','Recommended Action':'D'}
])

print("Input rows:", len(sample))
merged = gen._deduplicate_failures(sample)
print("Merged rows:", len(merged))
print(merged.to_dict(orient='records'))
