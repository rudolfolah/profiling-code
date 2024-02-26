from bs4 import BeautifulSoup
import requests

from collections import Counter
import tempfile

r = requests.get("https://en.wikipedia.org/wiki/Intuitive_Machines_Nova-C")
with tempfile.NamedTemporaryFile(delete=False) as temp:
    temp.write(r.content)
    temp.flush()
    temp_filename = temp.name

with open(temp_filename, "r") as file:
    soup = BeautifulSoup(file, "html.parser")
    words = Counter()
    for paragraph in soup.find_all("p"):
        for word in paragraph.text.split():
            if len(word) > 3:
                words[word] += 1

print(words.most_common(10))
