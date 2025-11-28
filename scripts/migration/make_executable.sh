#!/bin/bash
# Make all migration scripts executable
# Run this once after cloning the repo

chmod +x scripts/migration/01_setup_vm.sh
chmod +x scripts/migration/02_migrate_to_vm.sh
chmod +x scripts/migration/03_verify_vm.sh

echo "All migration scripts are now executable"
