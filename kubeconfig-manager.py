#!/usr/bin/env python
"""
Kubeconfig Manager - A CLI tool for managing Kubernetes configurations
"""

import os
import sys
import json
import shutil
import click
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class KubeconfigManager:
    def __init__(self):
        self.default_config_path = Path.home() / ".kube" / "config"
        self.backup_dir = Path.home() / ".kube" / "backups"
        self.profiles_dir = Path.home() / ".kube" / "profiles"
        self.profiles_config = self.profiles_dir / "profiles.json"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
    def get_profiles(self) -> Dict:
        """Load profile configuration"""
        if not self.profiles_config.exists():
            return {"profiles": {}, "current_profile": "default"}
        
        try:
            with open(self.profiles_config, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"profiles": {}, "current_profile": "default"}
    
    def save_profiles(self, profiles_data: Dict):
        """Save profile configuration"""
        with open(self.profiles_config, "w") as f:
            json.dump(profiles_data, f, indent=2)
    
    def get_profile_config_path(self, profile_name: str) -> Path:
        """Get the config path for a specific profile"""
        if profile_name == "default":
            return self.default_config_path
        return self.profiles_dir / f"{profile_name}_config"
    
    def create_profile(self, profile_name: str, description: str = "") -> bool:
        """Create a new profile"""
        profiles_data = self.get_profiles()
        
        if profile_name in profiles_data["profiles"]:
            return False
        
        profiles_data["profiles"][profile_name] = {
            "description": description,
            "created": datetime.now().isoformat(),
            "config_path": str(self.get_profile_config_path(profile_name))
        }
        
        self.save_profiles(profiles_data)
        
        # Create empty config file for the profile
        config_path = self.get_profile_config_path(profile_name)
        if not config_path.exists():
            empty_config = {"clusters": [], "users": [], "contexts": [], "current-context": ""}
            self.save_config(empty_config, config_path)
        
        return True
    
    def switch_profile(self, profile_name: str) -> bool:
        """Switch to a different profile"""
        profiles_data = self.get_profiles()
        
        if profile_name != "default" and profile_name not in profiles_data["profiles"]:
            return False
        
        profiles_data["current_profile"] = profile_name
        self.save_profiles(profiles_data)
        return True
    
    def get_current_profile(self) -> str:
        """Get the current active profile"""
        profiles_data = self.get_profiles()
        return profiles_data.get("current_profile", "default")
    
    def get_current_config_path(self) -> Path:
        """Get the config path for the current profile"""
        current_profile = self.get_current_profile()
        return self.get_profile_config_path(current_profile)
    
    def detect_conflicts(self, base_config: Dict, new_config: Dict) -> List[Dict]:
        """Detect conflicts between configurations"""
        conflicts = []
        
        # Check for cluster conflicts
        base_clusters = {c.get("name"): c for c in base_config.get("clusters", [])}
        for cluster in new_config.get("clusters", []):
            cluster_name = cluster.get("name")
            if cluster_name in base_clusters:
                base_cluster = base_clusters[cluster_name]
                if cluster != base_cluster:
                    conflicts.append({
                        "type": "cluster",
                        "name": cluster_name,
                        "base": base_cluster,
                        "new": cluster
                    })
        
        # Check for user conflicts
        base_users = {u.get("name"): u for u in base_config.get("users", [])}
        for user in new_config.get("users", []):
            user_name = user.get("name")
            if user_name in base_users:
                base_user = base_users[user_name]
                if user != base_user:
                    conflicts.append({
                        "type": "user",
                        "name": user_name,
                        "base": base_user,
                        "new": user
                    })
        
        # Check for context conflicts
        base_contexts = {c.get("name"): c for c in base_config.get("contexts", [])}
        for context in new_config.get("contexts", []):
            context_name = context.get("name")
            if context_name in base_contexts:
                base_context = base_contexts[context_name]
                if context != base_context:
                    conflicts.append({
                        "type": "context",
                        "name": context_name,
                        "base": base_context,
                        "new": context
                    })
        
        return conflicts
    
    def preview_merge(self, base_config: Dict, new_config: Dict) -> Dict:
        """Preview what the merged config would look like"""
        return self.merge_configs(base_config, new_config)
    
    def interactive_context_selector(self, contexts: List[Dict]) -> Optional[str]:
        """Interactive context selection with fuzzy search"""
        if not contexts:
            return None
        
        context_names = [ctx.get("name", "") for ctx in contexts if ctx.get("name")]
        
        if len(context_names) == 1:
            return context_names[0]
        
        click.echo("\n🔍 Select a context:")
        for i, name in enumerate(context_names, 1):
            ctx = next(c for c in contexts if c.get("name") == name)
            cluster = ctx.get("context", {}).get("cluster", "Unknown")
            click.echo(f"  {i}. {name} (cluster: {cluster})")
        
        while True:
            try:
                choice = click.prompt("\nEnter number or context name", type=str)
                
                # Try as number first
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(context_names):
                        return context_names[idx]
                except ValueError:
                    pass
                
                # Try as context name or partial match
                matches = [name for name in context_names if choice.lower() in name.lower()]
                if len(matches) == 1:
                    return matches[0]
                elif len(matches) > 1:
                    click.echo(f"Multiple matches: {', '.join(matches)}")
                    continue
                else:
                    click.echo("No matches found")
                    continue
                    
            except click.Abort:
                return None
    
    def apply_conflict_resolutions(self, base_config: Dict, new_config: Dict, conflicts: List[Dict]) -> Dict:
        """Apply conflict resolutions based on user choices"""
        merged = self.merge_configs(base_config, new_config)
        
        for conflict in conflicts:
            if conflict.get('resolution') == 'base':
                # Keep the base version
                if conflict['type'] == 'cluster':
                    clusters = [c for c in merged['clusters'] if c.get('name') != conflict['name']]
                    clusters.append(conflict['base'])
                    merged['clusters'] = clusters
                elif conflict['type'] == 'user':
                    users = [u for u in merged['users'] if u.get('name') != conflict['name']]
                    users.append(conflict['base'])
                    merged['users'] = users
                elif conflict['type'] == 'context':
                    contexts = [c for c in merged['contexts'] if c.get('name') != conflict['name']]
                    contexts.append(conflict['base'])
                    merged['contexts'] = contexts
        
        return merged

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
    help="Target config file (default: current profile)",
)
@click.option("--profile", "-p", help="Target profile (overrides --target)")
@click.option("--backup/--no-backup", default=True, help="Create backup before merging")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--interactive", "-i", is_flag=True, help="Interactive conflict resolution")
def add(config_file, target, profile, backup, dry_run, interactive):
    """Add a new kubeconfig file to your existing configuration"""
    manager = KubeconfigManager()

    # Determine target config path
    if profile:
        if not manager.switch_profile(profile):
            raise click.ClickException(f"Profile '{profile}' not found")
        target = manager.get_profile_config_path(profile)
    elif target is None:
        target = manager.get_current_config_path()
    else:
        target = Path(target)

    config_file = Path(config_file)
    current_profile = manager.get_current_profile()

    click.echo(f"📁 Adding config from: {config_file}")
    click.echo(f"📁 To target config: {target}")
    click.echo(f"📁 Current profile: {current_profile}")

    # Load configs
    base_config = manager.load_config(target)
    new_config = manager.load_config(config_file)

    # Detect conflicts
    conflicts = manager.detect_conflicts(base_config, new_config)
    
    if conflicts:
        click.echo(f"\n⚠️  Found {len(conflicts)} conflicts:")
        for conflict in conflicts:
            click.echo(f"   - {conflict['type']}: {conflict['name']}")
        
        if interactive:
            click.echo("\n🔧 Conflict Resolution:")
            for conflict in conflicts:
                click.echo(f"\nConflict in {conflict['type']}: {conflict['name']}")
                click.echo("Choose which version to keep:")
                click.echo("1. Keep existing (base)")
                click.echo("2. Use new (incoming)")
                choice = click.prompt("Choice", type=click.Choice(['1', '2']))
                conflict['resolution'] = 'base' if choice == '1' else 'new'
        elif not dry_run:
            if not click.confirm("\nProceed with merge? (new config will overwrite conflicts)"):
                click.echo("❌ Operation cancelled")
                return

    # Preview merge
    merged_config = manager.preview_merge(base_config, new_config)
    
    # Apply conflict resolutions if interactive mode
    if interactive and conflicts:
        merged_config = manager.apply_conflict_resolutions(base_config, new_config, conflicts)

    # Show preview
    click.echo("\n📊 Preview:")
    click.echo(f"   Clusters: {len(base_config.get('clusters', []))} → {len(merged_config.get('clusters', []))}")
    click.echo(f"   Users: {len(base_config.get('users', []))} → {len(merged_config.get('users', []))}")
    click.echo(f"   Contexts: {len(base_config.get('contexts', []))} → {len(merged_config.get('contexts', []))}")
    click.echo(f"   Current context: {merged_config.get('current-context', 'None')}")

    if dry_run:
        click.echo("\n🔍 Dry run complete - no changes made")
        return

    # Create backup if requested and target exists
    if backup and target.exists():
        backup_path = manager.backup_config(target)
        if backup_path:
            click.echo(f"\n📦 Backup created: {backup_path}")

    # Save merged config
    manager.save_config(merged_config, target)
    click.echo("\n✅ Configuration merged successfully!")


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
@click.argument("context_name", required=False)
@click.option(
    "--config", "-c", type=click.Path(), help="Config file to switch context in"
)
@click.option("--profile", "-p", help="Profile to switch context in")
@click.option("--interactive", "-i", is_flag=True, help="Interactive context selection")
def switch(context_name, config, profile, interactive):
    """Switch to a different context"""
    manager = KubeconfigManager()

    # Determine config path
    if profile:
        if not manager.switch_profile(profile):
            raise click.ClickException(f"Profile '{profile}' not found")
        config_path = manager.get_profile_config_path(profile)
    elif config:
        config_path = Path(config)
    else:
        config_path = manager.get_current_config_path()

    if not config_path.exists():
        raise click.ClickException(f"Config file not found: {config_path}")

    # Interactive mode or direct switch
    if interactive or not context_name:
        contexts = manager.list_contexts(config_path)
        if not contexts:
            click.echo("❌ No contexts available")
            return
        
        if interactive:
            selected_context = manager.interactive_context_selector(contexts)
            if not selected_context:
                click.echo("❌ No context selected")
                return
            context_name = selected_context
        else:
            # Show available contexts
            current_profile = manager.get_current_profile()
            click.echo(f"\n📋 Available contexts in profile '{current_profile}':")
            config_data = manager.load_config(config_path)
            current_context = config_data.get("current-context", "")
            
            for ctx in contexts:
                name = ctx.get("name", "Unknown")
                cluster = ctx.get("context", {}).get("cluster", "Unknown")
                marker = "👉" if name == current_context else "  "
                click.echo(f"{marker} {name} (cluster: {cluster})")
            return

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


# Profile management commands
@cli.group()
def profile():
    """Profile management commands"""
    pass

@profile.command("create")
@click.argument("profile_name")
@click.option("--description", "-d", help="Profile description")
def create_profile(profile_name, description):
    """Create a new profile"""
    manager = KubeconfigManager()
    
    if manager.create_profile(profile_name, description or ""):
        click.echo(f"✅ Profile '{profile_name}' created successfully")
    else:
        click.echo(f"❌ Profile '{profile_name}' already exists")

@profile.command("list")
def list_profiles():
    """List all profiles"""
    manager = KubeconfigManager()
    profiles_data = manager.get_profiles()
    current_profile = profiles_data.get("current_profile", "default")
    
    click.echo("📋 Available profiles:\n")
    
    # Show default profile
    marker = "👉" if current_profile == "default" else "  "
    click.echo(f"{marker} default (system default)")
    
    # Show custom profiles
    for name, info in profiles_data.get("profiles", {}).items():
        marker = "👉" if current_profile == name else "  "
        description = info.get("description", "")
        created = info.get("created", "")
        click.echo(f"{marker} {name}")
        if description:
            click.echo(f"     Description: {description}")
        if created:
            try:
                created_date = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")
                click.echo(f"     Created: {created_date}")
            except ValueError:
                pass
        click.echo()

@profile.command("switch")
@click.argument("profile_name")
def switch_profile_cmd(profile_name):
    """Switch to a different profile"""
    manager = KubeconfigManager()
    
    if manager.switch_profile(profile_name):
        click.echo(f"🔄 Switched to profile: {profile_name}")
    else:
        click.echo(f"❌ Profile '{profile_name}' not found")
        
        # Show available profiles
        profiles_data = manager.get_profiles()
        available = ["default"] + list(profiles_data.get("profiles", {}).keys())
        click.echo(f"Available profiles: {', '.join(available)}")

@profile.command("current")
def current_profile():
    """Show current active profile"""
    manager = KubeconfigManager()
    current = manager.get_current_profile()
    config_path = manager.get_current_config_path()
    
    click.echo(f"Current profile: {current}")
    click.echo(f"Config path: {config_path}")
    
    if config_path.exists():
        config = manager.load_config(config_path)
        contexts = config.get("contexts", [])
        current_context = config.get("current-context", "None")
        click.echo(f"Contexts: {len(contexts)}")
        click.echo(f"Current context: {current_context}")

@profile.command("delete")
@click.argument("profile_name")
@click.confirmation_option(prompt="Are you sure you want to delete this profile?")
def delete_profile(profile_name):
    """Delete a profile"""
    manager = KubeconfigManager()
    
    if profile_name == "default":
        click.echo("❌ Cannot delete the default profile")
        return
    
    profiles_data = manager.get_profiles()
    
    if profile_name not in profiles_data.get("profiles", {}):
        click.echo(f"❌ Profile '{profile_name}' not found")
        return
    
    # Remove profile from config
    del profiles_data["profiles"][profile_name]
    
    # Switch to default if this was the current profile
    if profiles_data.get("current_profile") == profile_name:
        profiles_data["current_profile"] = "default"
    
    manager.save_profiles(profiles_data)
    
    # Remove profile config file
    config_path = manager.get_profile_config_path(profile_name)
    if config_path.exists():
        config_path.unlink()
    
    click.echo(f"✅ Profile '{profile_name}' deleted")

if __name__ == "__main__":
    cli()
