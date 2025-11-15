# Agents Overview – `model_checkpoints/`
- Stores learned weights that power runtime models.
- `implicit_model_weights.pth` contains the MLP used by the coordinate transfer server to map image detections into table coordinates.
- Managed at runtime by `scripts/coordinate_transfer.py`.

