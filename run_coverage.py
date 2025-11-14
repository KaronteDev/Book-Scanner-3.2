import coverage, pytest

if __name__ == '__main__':
    cov = coverage.Coverage(source=['models','presenters','services'])
    cov.start()
    # Run pytest with default discovery
    pytest.main([])
    cov.stop()
    cov.save()
    print('\nCOVERAGE REPORT')
    cov.report()
