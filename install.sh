#!/usr/bin/env bash

# Change this to the location in which the zygrader directory is cloned
# For example:
# $ mkdir ~/grading && cd ~/grading
# $ git clone https://github.com/natecraddock/zygrader
# Then INSTALL_PATH would be ~/grading
INSTALL_PATH="/users/groups/cs142ta/tools/zygrader"

echo ZYGRADER INSTALLER
echo ""
echo ""

# Ensure running from the correct dir
cd $INSTALL_PATH

# Cleanup old dirs if needed
if test -f "$HOME/Desktop/zygrader"; then
    rm $HOME/Desktop/zygrader
fi
if test -f "$HOME/.zygrader/zygrader"; then
    rm $HOME/.zygrader/zygrader
fi

# Create zygrader config directory
if [ ! -d "$HOME/.zygrader" ]; then
    mkdir $HOME/.zygrader
fi

# Add zygrader directory to path for easy execution
if [[ ":$PATH:" == *":$HOME/.zygrader:"* ]] ; then
    echo "zygrader is already in the path"
else
    echo "adding zygrader to the path"
    echo "# Zygrader path" >> $HOME/.bashrc
    echo "export PATH=\$PATH:$HOME/.zygrader" >> $HOME/.bashrc
fi

# Install zygrader locally
ln -s $PWD/zygrader/__main__.py $HOME/.zygrader/zygrader
chmod u+x $HOME/.zygrader/zygrader

# Add zygrader shell script to desktop
ln -s $PWD/zygrader/__main__.py $HOME/Desktop/zygrader
chmod u+x $HOME/Desktop/zygrader

echo zygrader is now installed, to run type zygrader in a new terminal
echo or run the zygrader file that has been copied to your desktop
echo ""

