from app import app as application  # Import your app

import nltk

# Download vader_lexicon if not already downloaded
try:
    nltk.data.find('sentiment/vader_lexicon')
except LookupError:
    # This ensures the lexicon is downloaded to the correct directory
    nltk.download('vader_lexicon', download_dir='/opt/render/project/src/nltk_data')

# Append the path to nltk_data for the app to use
nltk.data.path.append('/opt/render/project/src/nltk_data')
