#!/bin/bash
if [ -z "$1" ]
  then
    PREFIX=/usr/bin
  else
    PREFIX=$1
fi

rm -f $PREFIX/sharelatex-git
