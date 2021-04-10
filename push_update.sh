#!/usr/bin/env bash

# Requires the version number as an arg
if [ $# != 1 ]
then
    echo "Usage: $0 VERSION_NUMBER"
    exit
fi

# Ensure we are pushing the correct version
if ! grep -q $1 "./zygrader/config/shared.py";
then
    echo "$1 is not the current version in ./zygrader/config/shared.py!"
    exit
fi

# Check if most recent commit includes a raise of version number
# to this current version.
if ! git show HEAD | grep -q $1;
then
    echo "The most recent commit did not bump version to $1"
    exit
fi

# Tag and push
git tag -m "Version $1" $1
git push --follow-tags
