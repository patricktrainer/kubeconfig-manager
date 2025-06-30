#!/usr/bin/env python
"""
Kubeconfig Manager - A CLI tool for managing Kubernetes configurations
"""

import shutil
import click
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class KubeconfigManager:
    def __init__(self):
        self.default_config_path = Path.home() / ".kube" / "config"
        self.backup_dir = Path.home() / ".kube" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self, config_path: Path) -> Dict:
        """Load a kubeconfig file"""
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {"clusters": [], "users": [], "contexts": [], "current-context": ""}
        except yaml.YAMLError as e:
            raise click.ClickException(f"Error parsing YAML in {config_path}: {e}")

    def save_config(self, config: Dict, config_path: Path):
        """Save a kubeconfig file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        click.echo(f"✅ Saved config to {config_path}")

    def backup_config(self, config_path: Path) -> Path:
        """Create a backup of the current config"""
        if not config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"config_backup_{timestamp}"
        shutil.copy2(config_path, backup_path)
        return backup_path

    def merge_configs(self, base_config: Dict, new_config: Dict) -> Dict:
        """Merge two kubeconfig files"""
        merged = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [],
            "users": [],
            "contexts": [],
            "current-context": base_config.get("current-context", ""),
        }

        # Merge clusters
        existing_clusters = {
            c.get("name"): c for c in base_config.get("clusters", []) if c.get("name")
        }
        for cluster in new_config.get("clusters", []):
            if cluster.get("name"):
                existing_clusters[cluster.get("name")] = cluster
        merged["clusters"] = list(existing_clusters.values())

        # Merge users
        existing_users = {
            u.get("name"): u for u in base_config.get("users", []) if u.get("name")
        }
        for user in new_config.get("users", []):
            if user.get("name"):
                existing_users[user.get("name")] = user
        merged["users"] = list(existing_users.values())

        # Merge contexts
        existing_contexts = {
            c.get("name"): c for c in base_config.get("contexts", []) if c.get("name")
        }
        for context in new_config.get("contexts", []):
            if context.get("name"):
                existing_contexts[context.get("name")] = context
        merged["contexts"] = list(existing_contexts.values())

        # Use new config's current-context if it exists
        if new_config.get("current-context"):
            merged["current-context"] = new_config["current-context"]

        return merged

    def list_contexts(self, config_path: Path = None) -> List[Dict]:
        """List all contexts in a config file"""
        if config_path is None:
            config_path = self.default_config_path

        config = self.load_config(config_path)
        return config.get("contexts", [])

    def switch_context(self, context_name: str, config_path: Path = None):
        """Switch to a different context"""
        if config_path is None:
            config_path = self.default_config_path

        config = self.load_config(config_path)
        contexts = [c.get("name") for c in config.get("contexts", [])]

        if context_name not in contexts:
            available = ", ".join(contexts) if contexts else "No contexts available"
            raise click.ClickException(
                f"Context '{context_name}' not found. Available: {available}"
            )

        # Backup before changing
        backup_path = self.backup_config(config_path)
        if backup_path:
            click.echo(f"📦 Backup created: {backup_path}")

        config["current-context"] = context_name
        self.save_config(config, config_path)
        click.echo(f"🔄 Switched to context: {context_name}")


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """🚀 Kubeconfig Manager - Simplify your Kubernetes configuration management"""
    pass


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--target",
    "-t",
    type=click.Path(),
    help="Target config file (default: ~/.kube/config)",
)
@click.option("--backup/--no-backup", default=True, help="Create backup before merging")
def add(config_file, target, backup):
    """Add a new kubeconfig file to your existing configuration"""
    manager = KubeconfigManager()

    if target is None:
        target = manager.default_config_path
    else:
        target = Path(target)

    config_file = Path(config_file)

    click.echo(f"📁 Adding config from: {config_file}")
    click.echo(f"📁 To target config: {target}")

    # Create backup if requested and target exists
    if backup and target.exists():
        backup_path = manager.backup_config(target)
        if backup_path:
            click.echo(f"📦 Backup created: {backup_path}")

    # Load configs
    base_config = manager.load_config(target)
    new_config = manager.load_config(config_file)

    # Merge configs
    merged_config = manager.merge_configs(base_config, new_config)

    # Save merged config
    manager.save_config(merged_config, target)

    # Show summary
    click.echo("\n📊 Summary:")
    click.echo(f"   Clusters: {len(merged_config.get('clusters', []))}")
    click.echo(f"   Users: {len(merged_config.get('users', []))}")
    click.echo(f"   Contexts: {len(merged_config.get('contexts', []))}")
    click.echo(f"   Current context: {merged_config.get('current-context', 'None')}")


@cli.command("list")
@click.option(
    "--config", "-c", type=click.Path(), help="Config file to list contexts from"
)
def list_contexts_cmd(config):
    """List all available contexts"""
    manager = KubeconfigManager()

    config_path = Path(config) if config else manager.default_config_path

    if not config_path.exists():
        click.echo("❌ No kubeconfig file found")
        return

    contexts = manager.list_contexts(config_path)

    if not contexts:
        click.echo("❌ No contexts found in config")
        return

    config_data = manager.load_config(config_path)
    current_context = config_data.get("current-context", "")

    click.echo(f"📋 Contexts in {config_path}:\n")

    for context in contexts:
        name = context.get("name", "Unknown")
        cluster = context.get("context", {}).get("cluster", "Unknown")
        user = context.get("context", {}).get("user", "Unknown")
        namespace = context.get("context", {}).get("namespace", "default")

        marker = "👉" if name == current_context else "  "
        click.echo(f"{marker} {name}")
        click.echo(f"     Cluster: {cluster}")
        click.echo(f"     User: {user}")
        click.echo(f"     Namespace: {namespace}")
        click.echo()


@cli.command()
@click.argument("context_name")
@click.option(
    "--config", "-c", type=click.Path(), help="Config file to switch context in"
)
def switch(context_name, config):
    """Switch to a different context"""
    manager = KubeconfigManager()

    config_path = Path(config) if config else manager.default_config_path

    if not config_path.exists():
        raise click.ClickException(f"Config file not found: {config_path}")

    manager.switch_context(context_name, config_path)


@cli.command()
@click.option("--config", "-c", type=click.Path(), help="Config file to validate")
def validate(config):
    """Validate a kubeconfig file"""
    manager = KubeconfigManager()

    config_path = Path(config) if config else manager.default_config_path

    if not config_path.exists():
        click.echo(f"❌ Config file not found: {config_path}")
        return

    try:
        config_data = manager.load_config(config_path)

        # Basic validation
        required_fields = ["clusters", "users", "contexts"]
        missing_fields = [
            field for field in required_fields if field not in config_data
        ]

        if missing_fields:
            click.echo(f"❌ Missing required fields: {', '.join(missing_fields)}")
            return

        # Check for empty sections
        empty_sections = [field for field in required_fields if not config_data[field]]

        if empty_sections:
            click.echo(f"⚠️  Empty sections: {', '.join(empty_sections)}")

        # Validate current-context exists
        current_context = config_data.get("current-context")
        context_names = [c.get("name") for c in config_data.get("contexts", [])]

        if current_context and current_context not in context_names:
            click.echo(f"❌ Current context '{current_context}' not found in contexts")
            return

        click.echo("✅ Kubeconfig file is valid!")

        # Show summary
        click.echo(f"\n📊 Summary:")
        click.echo(f"   File: {config_path}")
        click.echo(f"   Clusters: {len(config_data.get('clusters', []))}")
        click.echo(f"   Users: {len(config_data.get('users', []))}")
        click.echo(f"   Contexts: {len(config_data.get('contexts', []))}")
        click.echo(f"   Current context: {current_context or 'None'}")

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}")


@cli.command()
def backups():
    """List available backups"""
    manager = KubeconfigManager()

    if not manager.backup_dir.exists():
        click.echo("❌ No backup directory found")
        return

    backup_files = list(manager.backup_dir.glob("config_backup_*"))

    if not backup_files:
        click.echo("❌ No backups found")
        return

    click.echo(f"📦 Available backups in {manager.backup_dir}:\n")

    for backup_file in sorted(backup_files, reverse=True):
        # Parse timestamp from filename
        timestamp_str = backup_file.name.replace("config_backup_", "")
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted_time = timestamp_str

        file_size = backup_file.stat().st_size
        click.echo(f"   📄 {backup_file.name}")
        click.echo(f"      Created: {formatted_time}")
        click.echo(f"      Size: {file_size} bytes")
        click.echo()


@cli.command()
@click.argument("backup_name")
@click.option(
    "--target",
    "-t",
    type=click.Path(),
    help="Target config file (default: ~/.kube/config)",
)
def restore(backup_name, target):
    """Restore from a backup"""
    manager = KubeconfigManager()

    backup_path = manager.backup_dir / backup_name

    if not backup_path.exists():
        click.echo(f"❌ Backup not found: {backup_name}")
        click.echo("Use 'kubeconfig-manager backups' to list available backups")
        return

    if target is None:
        target = manager.default_config_path
    else:
        target = Path(target)

    # Create a backup of current config before restoring
    if target.exists():
        current_backup = manager.backup_config(target)
        if current_backup:
            click.echo(f"📦 Current config backed up to: {current_backup}")

    # Restore the backup
    shutil.copy2(backup_path, target)
    click.echo(f"✅ Restored {backup_name} to {target}")


if __name__ == "__main__":
    cli()
