#!/usr/bin/env bash

cat docs/spelling_wordlist.txt > docs/tmpspell.txt
if [ -f ".idea/dictionaries/${USER}.xml" ]; then
  grep '<w>' .idea/dictionaries/${USER}.xml | sed -r 's/ *<w>(.*)<\/w>/\1/' >> docs/tmpspell.txt
fi
sort -u docs/tmpspell.txt > docs/spelling_wordlist.txt
rm docs/tmpspell.txt
