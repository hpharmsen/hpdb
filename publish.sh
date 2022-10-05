rm dist/*
python bumpversion.py patch
python -m build
twine upload dist/*
git commit -v -a -m "publish `date`"
git push
