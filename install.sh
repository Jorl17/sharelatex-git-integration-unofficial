#!/bin/bash
if [ -z "$1" ]
  then
    PREFIX=/usr/bin
  else
    PREFIX=$1
fi

cp sharelatex-git $PREFIX
chmod +x $PREFIX/sharelatex-git

