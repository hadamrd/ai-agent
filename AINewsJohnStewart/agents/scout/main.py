# Initialize the digger
from AINewsJohnStewart.agents.scout.digger import Digger


digger = Digger()

# Get and score articles
shortlisted = digger.dig_for_news(
    query="artificial intelligence",
    page_size=20,
    threshold=6
)

# Print results
for article in shortlisted:
    print(f"Score {article['score']}: {article['title']}")
    print(f"Reason: {article['reason']}\n")