rm dist/*
pip install build
pip install twine
python bumpversion.py patch
python -m build
twine upload dist/*
git commit -v -a -m "publish `date`"
git push
