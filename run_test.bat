@echo off
echo ================================================================================
echo TESTING DYNAMIC NETWORK EXPANSION
echo ================================================================================
python test_dynamic_expansion.py
echo.
echo.
echo ================================================================================
echo TEST COMPLETE! Press any key to start Streamlit app...
echo ================================================================================
pause
streamlit run app.py
