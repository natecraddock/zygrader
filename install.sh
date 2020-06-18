#!/usr/bin/env bash

# Change this to the location in which the zygrader directory is cloned
# For example:
# $ mkdir ~/grading && cd ~/grading
# $ git clone https://github.com/natecraddock/zygrader
# Then INSTALL_PATH would be ~/grading
INSTALL_PATH="/users/groups/cs142ta/tools/zygrader"
USER_PATH="$HOME/.config/zygrader"
DESKTOP_PATH="$HOME/Desktop"

USER_PATH_LEGACY="$HOME/.zygrader"

echo ZYGRADER INSTALLER
echo ""

# Ensure running from the correct dir
cd $INSTALL_PATH

# Cleanup old dirs if needed
if test -f "$DESKTOP_PATH/zygrader"; then
    rm "$DESKTOP_PATH/zygrader"
fi
if test -d "$USER_PATH"; then
    rm -r $USER_PATH
fi

# Create zygrader config directory
if [ ! -d $USER_PATH ]; then
    mkdir -p $USER_PATH
fi

# Copy config from the older (pre 3.6) config dir if it exists
if test -d $USER_PATH_LEGACY; then
    mv $USER_PATH_LEGACY/config $USER_PATH/config.json
    rm -r $USER_PATH_LEGACY
    echo "Copied previous config to new directory"
fi

# Add zygrader directory to path for easy execution
if [[ ":$PATH:" == *":$USER_PATH:"* ]] ; then
    echo "zygrader is already in the path"
else
    echo "adding zygrader to the path"
    echo "# Zygrader path" >> $HOME/.bashrc
    echo "export PATH=\$PATH:$USER_PATH" >> $HOME/.bashrc
    echo "" >> $HOME/.bashrc
fi

# Install zygrader locally
ln -s $PWD/zygrader/__main__.py $USER_PATH/zygrader
chmod u+x $USER_PATH/zygrader

# Add zygrader to desktop as well
ln -s $PWD/zygrader/__main__.py $DESKTOP_PATH/zygrader
chmod u+x $HOME/Desktop/zygrader

echo ""
echo zygrader is now installed, to run, execute zygrader in a new terminal
echo or run the zygrader file that has been copied to your desktop
echo ""

