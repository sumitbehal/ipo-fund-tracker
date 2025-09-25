import requests
from bs4 import BeautifulSoup

def scrape_ipo():
    url = "https://www.chittorgarh.com/calendar/ipo-calendar/1/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/116.0.0.0 Safari/537.36"
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()  # Will raise an error if request fails
    soup = BeautifulSoup(res.text, "html.parser")

    ipo_list = []

    # Adjust these selectors according to the page structure
    table = soup.find("table", {"class": "tblIPO"})  # Example table class
    rows = table.find_all("tr")[1:]  # Skip header row

    for row in rows:
        cols = row.find_all("td")
        ipo_data = {
            "name": cols[0].text.strip(),
            "open_date": cols[1].text.strip(),
            "close_date": cols[2].text.strip(),
            "gmp": float(cols[3].text.strip().replace('%','')) if cols[3].text.strip() else 0,
            "retail_shares": cols[4].text.strip(),
            "retail_amount": cols[5].text.strip(),
            "hni_shares": cols[6].text.strip(),
            "hni_amount": cols[7].text.strip(),
            "bhni_shares": cols[8].text.strip(),
            "bhni_amount": cols[9].text.strip()
        }
        ipo_list.append(ipo_data)

    return ipo_list
