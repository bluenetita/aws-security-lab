# AWS infrastructure artifacts

Historical AWS configuration templates for the EC2/VPC laboratory are provided for review:

- `http-mirror-filter.rules.json`: Traffic Mirroring filter example.
- `zeek-run-instances.template.json`: EC2 launch template with placeholders; **not the source of truth for existing instances**.
- `../../config/lab.example.json`: local operator configuration schema with placeholder identifiers.

The environment used a private VPC/subnet, source and target ENIs and temporary Traffic Mirroring sessions. Sessions must be explicitly deleted after approved experiments to stop mirroring and its associated charges. For verified experiments see [experimental results](../../docs/experimental-results.md); for read-only inspection and lifecycle commands see [operations](../../docs/operations.md).

Templates must be reviewed and adapted before use. They are **not evidence** that a new AWS resource has been provisioned.
