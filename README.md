# Kubeconfig Manager

🚀 A powerful CLI tool for managing Kubernetes configurations with profile support, interactive modes, and advanced safety features.

## Features

- 📁 **Profile Management** - Organize configurations by environment (dev, staging, prod)
- 🔄 **Smart Merging** - Intelligently merge kubeconfig files with conflict detection
- 🎯 **Interactive Mode** - Fuzzy search and guided context switching
- 🔍 **Dry Run** - Preview changes before applying them
- ⚡ **Conflict Resolution** - Handle duplicate contexts with user guidance
- 📦 **Automatic Backups** - Never lose your configurations
- ✅ **Validation** - Ensure your kubeconfig files are valid

## Installation

```bash
# Make the script executable
chmod +x kubeconfig-manager.py

# Optionally, create a symlink for easier access
ln -s $(pwd)/kubeconfig-manager.py /usr/local/bin/kcman
```

## Quick Start

```bash
# View current profile and contexts
kcman profile current
kcman switch

# Create a new profile for development
kcman profile create dev --description "Development environment"
kcman profile switch dev

# Add a kubeconfig file with preview
kcman add ~/.kube/new-cluster.yaml --dry-run

# Add with interactive conflict resolution
kcman add ~/.kube/new-cluster.yaml --interactive

# Switch contexts interactively
kcman switch --interactive
```

## Command Reference

### Profile Management

#### Create a Profile
```bash
kcman profile create <profile-name> [--description "Description"]
```

#### List Profiles
```bash
kcman profile list
```

#### Switch Profile
```bash
kcman profile switch <profile-name>
```

#### Show Current Profile
```bash
kcman profile current
```

#### Delete Profile
```bash
kcman profile delete <profile-name>
```

### Configuration Management

#### Add Kubeconfig
```bash
# Basic usage
kcman add <config-file>

# With options
kcman add <config-file> [OPTIONS]
  --profile, -p TEXT      Target profile
  --target, -t PATH       Target config file
  --dry-run              Preview changes only
  --interactive, -i      Interactive conflict resolution
  --backup/--no-backup   Create backup (default: yes)
```

#### Switch Context
```bash
# List available contexts
kcman switch

# Switch to specific context
kcman switch <context-name>

# Interactive context selection
kcman switch --interactive

# Switch in specific profile
kcman switch <context-name> --profile <profile-name>
```

#### List Contexts
```bash
# List contexts in current profile
kcman list

# List contexts in specific config
kcman list --config <config-file>
```

### Backup & Restore

#### List Backups
```bash
kcman backups
```

#### Restore from Backup
```bash
kcman restore <backup-name>
```

### Validation

#### Validate Configuration
```bash
# Validate current profile's config
kcman validate

# Validate specific file
kcman validate --config <config-file>
```

## Usage Examples

### Setting Up Multiple Environments

```bash
# Create profiles for different environments
kcman profile create development --description "Dev clusters"
kcman profile create staging --description "Staging environment"
kcman profile create production --description "Production clusters"

# Switch to development profile
kcman profile switch development

# Add development clusters
kcman add ~/.kube/dev-cluster-1.yaml
kcman add ~/.kube/dev-cluster-2.yaml

# Switch to production profile and add prod clusters
kcman profile switch production
kcman add ~/.kube/prod-cluster.yaml --interactive
```

### Safe Configuration Updates

```bash
# Preview what will change
kcman add new-config.yaml --dry-run

# Add with conflict resolution
kcman add new-config.yaml --interactive

# Validate the result
kcman validate
```

### Interactive Workflows

```bash
# Interactive context switching with search
kcman switch --interactive

# Interactive conflict resolution
kcman add conflicting-config.yaml --interactive
```

## Configuration Structure

The tool stores configurations in:

```
~/.kube/
├── config                          # Default kubeconfig
├── backups/                        # Automatic backups
│   ├── config_backup_20231201_143022
│   └── config_backup_20231201_143045
└── profiles/                       # Profile management
    ├── profiles.json               # Profile metadata
    ├── dev_config                  # Development profile config
    ├── staging_config              # Staging profile config
    └── production_config           # Production profile config
```

## Safety Features

### Automatic Backups
- Every modification creates a timestamped backup
- Backups are stored in `~/.kube/backups/`
- Use `kcman backups` to list and `kcman restore` to recover

### Conflict Detection
- Automatically detects conflicting clusters, users, and contexts
- Interactive resolution lets you choose which version to keep
- Preview mode shows exactly what will change

### Dry Run Mode
- Preview all changes before applying
- Shows before/after counts for all resources
- No modifications made in dry-run mode

### Validation
- Validates kubeconfig structure and references
- Checks for missing required fields
- Verifies current-context exists

## Advanced Usage

### Profile-Specific Operations

```bash
# Add config to specific profile without switching
kcman add config.yaml --profile staging

# Switch context in specific profile
kcman switch my-context --profile production

# Validate specific profile
kcman profile switch staging && kcman validate
```

### Batch Operations

```bash
# Add multiple configs with preview
for config in ~/.kube/clusters/*.yaml; do
  kcman add "$config" --dry-run
done

# Then apply after review
for config in ~/.kube/clusters/*.yaml; do
  kcman add "$config" --interactive
done
```

### Scripting Support

```bash
# Check current profile in scripts
CURRENT_PROFILE=$(kcman profile current | grep "Current profile:" | cut -d: -f2 | xargs)

# Programmatic context switching
kcman switch production-cluster --profile production
```

## Troubleshooting

### Common Issues

**Profile not found**
```bash
# List available profiles
kcman profile list

# Create if missing
kcman profile create <profile-name>
```

**Config file not found**
```bash
# Check current profile's config path
kcman profile current

# Validate the config
kcman validate
```

**Context switching fails**
```bash
# List available contexts
kcman switch

# Use interactive mode for guidance
kcman switch --interactive
```

### Recovery

**Restore from backup**
```bash
# List available backups
kcman backups

# Restore specific backup
kcman restore config_backup_20231201_143022
```

**Reset to clean state**
```bash
# Switch to default profile
kcman profile switch default

# Validate current state
kcman validate
```

## Requirements

- Python 3.7+
- PyYAML
- Click

```bash
pip install pyyaml click
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- 🐛 **Issues**: Report bugs and request features
- 📖 **Documentation**: Check this README for detailed usage
- 💡 **Tips**: Use `--help` with any command for detailed options

---

**Made with ❤️ for Kubernetes users who manage multiple clusters and environments.**