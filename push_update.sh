#!/usr/bin/env bash

if [ $# != 1 ]
then
    echo "Usage: $0 VERSION_NUMBER"
    exit
fi

git tag -m "Version $1" $1
git push --follow-tags
