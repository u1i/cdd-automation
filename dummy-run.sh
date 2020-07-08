echo $RANDOM > test.txt
git add -A
git commit -m changed-$(date +%s)
git push
