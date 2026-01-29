# NeuroMANCER HVAC Examples

This directory contains HVAC control examples copied from NeuroMANCER.

## Source

These examples are copied from:
https://github.com/pnnl/neuromancer/tree/master/examples/building_systems

## Files

After running setup.sh, this directory will contain:
- Key HVAC control examples from NeuroMANCER
- Building thermal dynamics tutorials
- Safe DPC implementations

## Full Examples

For the complete set of examples, see:
- `../neuromancer_repo/examples/building_systems/` (local reference, not in Git)

## Usage

These files are tracked in Git so your team can:
- Reference the examples
- Modify for your specific needs
- Learn from NeuroMANCER implementations

To update to latest examples:
```bash
cd neuromancer_repo
git pull origin master
cd ..
cp neuromancer_repo/examples/building_systems/FILE.py neuromancer_examples/
git add neuromancer_examples/
git commit -m "Update HVAC examples"
```
