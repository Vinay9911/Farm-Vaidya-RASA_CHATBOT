from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import groq
import json
import logging
import re
from datetime import datetime, timedelta
import nltk
from nltk.tokenize import sent_tokenize

# Download NLTK data for sentence tokenization
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Cache for frequent queries with expiration
query_cache = {}  # {key: {"result": result, "timestamp": datetime}}
CACHE_EXPIRY = timedelta(hours=24)

def is_cache_valid(cache_entry):
    return datetime.now() - cache_entry["timestamp"] < CACHE_EXPIRY

# Extended spelling and synonym variation dictionary for normalization
SPELLING_VARIATIONS = {
    "fertiliser": "fertilizer",
    "fertilisers": "fertilizer",
    "manoeuvre": "maneuver",
    "manoeuvres": "maneuver",
    "colour": "color",
    "colours": "color",
    "organisation": "organization",
    "organisations": "organization",
    "manure": "manure",
    "manures": "manure",
    "compost": "manure",
    "organic fertilizer": "manure",
    "green manure": "manure",
    "vermicompost": "manure",
    "soil": "soil",
    "soils": "soil",
    "land": "soil",
    "ground": "soil",
    "earth": "soil",
    "variety": "variety",
    "varieties": "variety",
    "hybrid": "variety",
    "breed": "variety",
    "cultivar": "variety",
    "strain": "variety",
    "type": "variety",
    "kind": "variety",
    "intercrop": "intercrop",
    "intercrops": "intercrop",
    "research center": "research_station",
    "research institute": "research_station",
    "station": "research_station",
    "facility": "research_station",
    "nutrient": "fertilizer",
    "chemical": "fertilizer",
    "feed": "fertilizer",
    "weather": "climate",
    "environment": "climate",
    "conditions": "climate",
    "nut": "seed",
    "seedling": "seed",
    "propagule": "seed"
}

def normalize_spelling(text: str) -> str:
    """Normalize spelling variations and synonyms to a standard form."""
    words = text.split()
    normalized_words = []
    for word in words:
        # Remove punctuation for matching
        clean_word = re.sub(r'[^\w\s]', '', word.lower())
        # Check if the word matches any variation or synonym
        for variation, standard in SPELLING_VARIATIONS.items():
            if re.fullmatch(rf"{re.escape(variation)}(s)?", clean_word, re.IGNORECASE):
                normalized_words.append(standard)
                break
        else:
            normalized_words.append(clean_word)
    return " ".join(normalized_words)

class ActionClassifyIntent(Action):
    def name(self) -> Text:
        return "action_classify_intent"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        user_message = tracker.latest_message.get("text").lower()
        # Normalize spelling variations and synonyms
        normalized_message = normalize_spelling(user_message)
        logger.debug(f"Original message: {user_message}, Normalized message: {normalized_message}")

        intents = [
            "coconut_general", "climate_soils", "coconut_varieties", "cultivation_methods",
            "nutrient_management", "fertilizers", "inter_cultivation", "organic_manures"
        ]

        # Keyword-based fallback for robust classification (using normalized forms)
        keyword_map = {
            "nutrient_management": ["yellow", "yellowing", "spathe", "deficiency", "nitrogen", "phosphorus", "potash", "potassium", "barren", "drop", "symptoms", "mineral"],
            "cultivation_methods": ["nursery", "soil", "arrange", "planting", "seed", "seedling", "pit", "germination", "nut", "propagule"],
            "fertilizers": ["fertilizer", "urea", "potash", "manure", "neem cake", "super phosphate", "nutrient", "chemical", "feed"],
            "coconut_varieties": ["variety", "godavari ganga", "east coast tall", "double century", "gauthami ganga", "vasishta ganga", "vainateya ganga", "abhaya ganga", "hybrid", "breed", "cultivar", "strain", "type", "kind"],
            "climate_soils": ["climate", "soil", "rainfall", "humidity", "temperature", "irrigation", "drainage", "weather", "environment", "conditions", "land", "ground", "earth"],
            "coconut_general": ["cultivation", "area", "productivity", "district", "research", "ambajipeta", "yield increase", "research_station", "research center", "research institute", "facility"],
            "inter_cultivation": ["intercrop", "plow", "weed", "banana", "cocoa", "companion crop"],
            "organic_manures": ["manure", "compost", "vermicompost", "coconut waste", "green manure", "organic fertilizer"]
        }

        # Check cache
        classified_intent = tracker.get_slot("classified_intent")
        cache_key = f"classify_{normalized_message}_{classified_intent if classified_intent else 'none'}"
        if cache_key in query_cache and is_cache_valid(query_cache[cache_key]):
            logger.debug(f"Cache hit for query: {user_message}")
            result = query_cache[cache_key]["result"]
        else:
            # Keyword-based pre-check
            matched_intents = []
            for intent, keywords in keyword_map.items():
                for keyword in keywords:
                    # Match keyword with optional 's' for plural forms
                    pattern = rf"\b{re.escape(keyword)}(s)?\b"
                    if re.search(pattern, normalized_message, re.IGNORECASE):
                        matched_intents.append(intent)
                        break
            logger.debug(f"Keyword matches for {user_message}: {matched_intents}")

            if len(matched_intents) == 1:
                result = {"intent": matched_intents[0]}
                logger.debug(f"Keyword-based intent match: {matched_intents[0]}")
            else:
                # Initialize Groq client
                client = groq.Groq(api_key="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")

                # Prepare conversation history
                conversation_history = [
                    event.get("text") for event in tracker.events[-4:] if event.get("event") == "user"
                ]
                logger.debug(f"Conversation history for intent classification: {conversation_history}")

                # Prepare prompt for intent classification
                prompt = f"""
                You are an assistant for coconut cultivation queries. Classify the user's query into one of the following intents:
                {', '.join(intents)}.
                Use the following rules:
                - Queries about yellowing leaves, delayed spathes, or nutrient deficiencies (e.g., nitrogen, phosphorus, potash, minerals) → 'nutrient_management'.
                - Queries about nursery setup, soil type, seed/nut selection, planting, or germination → 'cultivation_methods'.
                - Queries about fertilizers, urea, potash, neem cake, nutrients, or chemicals → 'fertilizers'.
                - Queries about coconut varieties (e.g., Godavari Ganga, East Coast Tall), hybrids, breeds, cultivars, strains, types, or kinds → 'coconut_varieties'.
                - Queries about climate, weather, rainfall, humidity, soil types, or land conditions → 'climate_soils'.
                - Queries about area, productivity, districts, or research (e.g., Ambajipeta research station, research center, or facility) → 'coconut_general'.
                - Queries about intercrops, companion crops, plowing, or weed control → 'inter_cultivation'.
                - Queries about organic manures, compost, vermicompost, or green manure → 'organic_manures'.
                If the query is ambiguous or cannot be confidently classified, return 'ambiguous' and suggest a clarifying question based on likely intents.
                Consider the conversation history to classify follow-up queries accurately.
                Treat spelling variations (e.g., 'fertiliser'/'fertilizer') and synonyms (e.g., 'hybrid'/'variety', 'compost'/'manure', 'weather'/'climate', 'nut'/'seed') as equivalent for intent classification.
                Provide the response in JSON format with 'intent' and 'clarifying_question' (if applicable).

                Conversation history: {conversation_history}
                User query: {user_message}

                Examples:
                - "Suggest fertilizer schedule for coconut plants" → {{"intent": "fertilizers"}}
                - "Suggest nutrient management for 2 years old coconut plants?" → {{"intent": "fertilizers"}}
                - "Why are my coconut leaves yellow?" → {{"intent": "nutrient_management"}}
                - "What soil for coconut nursery?" → {{"intent": "cultivation_methods"}}
                - "How to grow coconuts?" → {{"intent": "ambiguous", "clarifying_question": "Could you specify if you're interested in cultivation methods, varieties, or fertilizers?"}}
                - History: ["Nutrient deficiency symptoms in coconuts"], Query: "nitrogen deficiency symptoms in coconut?" → {{"intent": "nutrient_management"}}
                - Query: "coconut varieties" → {{"intent": "coconut_varieties"}}
                - Query: "Which coconut hybrid is released by Ambajipeta?" → {{"intent": "coconut_varieties"}}
                - Query: "Coconut breed from research center Ambajipeta?" → {{"intent": "coconut_varieties"}}
                - Query: "Compost for coconut trees?" → {{"intent": "organic_manures"}}
                - Query: "Weather for coconut farming?" → {{"intent": "climate_soils"}}
                - Query: "How to select coconut nuts?" → {{"intent": "cultivation_methods"}}
                """
                
                try:
                    logger.debug(f"Sending query to Groq: {user_message}")
                    response = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=100
                    )
                    raw_response = response.choices[0].message.content
                    logger.debug(f"Groq raw response: {raw_response}")
                    result = json.loads(raw_response)
                    query_cache[cache_key] = {"result": result, "timestamp": datetime.now()}
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {e}, raw response: {raw_response}")
                    result = {"intent": "ambiguous", "clarifying_question": "Could you clarify your question about coconut cultivation?"}
                except Exception as e:
                    logger.error(f"Error in action_classify_intent: {e}")
                    result = {"intent": "ambiguous", "clarifying_question": "Sorry, I couldn't process your query. Please specify if it's about fertilizers, varieties, or another topic."}

        intent = result.get("intent")
        clarifying_question = result.get("clarifying_question")

        if intent == "ambiguous":
            clarifying_question = clarifying_question or f"Could you clarify if you're asking about cultivation methods, nutrient management, fertilizers, or another coconut-related topic?"
            dispatcher.utter_message(text=clarifying_question)
            return []
        else:
            logger.debug(f"Classified intent: {intent}")
            return [{"event": "slot", "name": "classified_intent", "value": intent}]

class ActionAnswerQuery(Action):
    def name(self) -> Text:
        return "action_answer_query"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        classified_intent = tracker.get_slot("classified_intent")
        user_message = tracker.latest_message.get("text").lower()
        normalized_message = normalize_spelling(user_message)  # Normalize for cache key

        if not classified_intent:
            logger.error("No classified intent found in slot")
            dispatcher.utter_message(text="I couldn't understand your query. Please specify if it's about coconut varieties, fertilizers, or another topic.")
            return []

        # Structured data from provided input
        data = {
            "coconut_general": {
                "overview": "Our state cultivates coconuts on 1.17 lakh hectares, ranking 4th in area after Kerala, Tamil Nadu, and Karnataka, and 1st in productivity. Over half the area is in the twin Godavari districts, with Guntur and Chittoor also significant. Scientific methods can boost yields in North Coast and Krishna areas.",
                "research": "Research at Ambajipeta Horticultural Research Station spans 70 years under Dr. Y.S.R. Horticultural University."
            },
            "climate_soils": {
                "climate": "Coastal areas with 1000-2000 mm rainfall and high humidity are ideal. Growth reduces below 15°C.",
                "soils": "Fertile delta lands or gravelly/red soils with irrigation and drainage are suitable. Inland areas are not ideal."
            },
            "coconut_varieties": {
                "East Coast Tall": "Widely grown in East Coast regions. Yields 75-100 nuts/year, 146g copra, 64% oil, fruits in 7 years.",
                "Godavari Ganga": "Hybrid developed in 1991 at Ambajipeta by crossing East Coast Tall and Ganga Bondam, released for Andhra Pradesh and Tamil Nadu. Yields 140 nuts/year, 150g copra, 68% oil, fruits in2 years.",
                "Double Century": "Released in 1994, suitable for East Coast. Yields 130 nuts/year, 160g copra, 64% oil, fruits in 7 years.",
                "Gauthami Ganga": "Selected from Ganga Bondam dwarf variety, released in 2017, ideal for tender coconuts. Yields 85-94 nuts/year, 157g copra, 69% oil, fruits in 4 years.",
                "Vasishta Ganga": "Hybrid developed in 2014 by crossing Ganga Bondam dwarf and Philippines Ordinary Tall, released for Andhra Pradesh and Karnataka. Yields 125 nuts/year, 158g copra, 69% oil, fruits in 4 years.",
                "Vainateya Ganga": "Hybrid developed in 2017 by crossing Philippines Ordinary Tall and Ganga Bondam dwarf, released for Andhra Pradesh. Yields 118 nuts/year, 190.5g copra, 66% oil, fruits in 4 years.",
                "Abhaya Ganga": "Hybrid developed in 2017 by crossing Ganga Bondam dwarf and Laccadive Ordinary Tall. Yields 136 nuts/year, 170g copra, 72% oil, fruits in 4 years."
            },
            "cultivation_methods": {
                "seed_selection": "Select nuts from 15-40-year-old trees yielding 100 nuts/year with 150g copra. Collect in April-May, dry for 20 days, plant in June.",
                "nursery": "Use light upland soils with drainage, plant nuts 30 cm between rows and 10-15 cm between nuts in a row. Irrigate frequently, control weeds/pests. Germination rate is 65-70%.",
                "planting": "Select 1-1.5-year-old seedlings, dig 1x1x1m pits in April-May, fill with 25kg manure + 500g super phosphate, plant 60 seedlings/acre in June-July."
            },
            "nutrient_management": {
                "phosphorus": "Strengthens seedling bases and leaf formation, aids nitrogen absorption. Apply 250g phosphorus with manure during planting.",
                "potash": "Speeds fruition, increases spathes, improves copra/oil yield, enhances pest/stress resistance.",
                "deficiencies": "Nitrogen: Yellow leaves, stunted growth, common in young plants. Phosphorus: Delayed spathes, poor nut maturity. Potash: Orange-yellow leaf spots, stunted trees, barren nuts, small nuts. General: Deficiencies in nitrogen or potash can cause improper flower setting or nut drop."
            },
            "fertilizers": {
                "young_trees": "For 1-4 years: 0.5kg urea + 1kg super phosphate + 1kg potash + 20kg manure/year/tree.",
                "mature_trees": "For >5 years: 1kg urea + 2kg super phosphate + 2.5kg potash + 25kg manure or 2kg neem cake/year/tree.",
                "application": "Apply in two splits (June-July, September-October) in a trench 3 feet from trunk, cover with soil, irrigate. Avoid unscientific methods like adding salt or cutting roots."
            },
            "inter_cultivation": {
                "plowing": "Plow rows twice yearly (early monsoon, post-rainy season) to control weeds.",
                "intercrops": "Grow banana, cocoa, or groundnut for additional income."
            },
            "organic_manures": {
                "role": "Stabilize yields by releasing nutrients slowly. Use with 50% chemical fertilizers.",
                "preparation": "Convert 16 tonnes/hectare of coconut waste (leaves, husks) into compost.",
                "benefits": "Retains moisture in light soils, increases organic carbon, boosts soil microorganisms, reduces salts/alkalinity, improves soil physical properties."
            }
        }

        if classified_intent not in data:
            logger.error(f"No data available for intent: {classified_intent}")
            dispatcher.utter_message(text="Sorry, I don't have information for that topic. Try asking about coconut varieties or fertilizers!")
            return []

        # Check cache
        cache_key = f"answer_{classified_intent}_{normalized_message}"
        if cache_key in query_cache and is_cache_valid(query_cache[cache_key]):
            logger.debug(f"Cache hit for query: {user_message}")
            answer = query_cache[cache_key]["result"]
        else:
            # Initialize Groq client
            client = groq.Groq(api_key="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")

            # Prepare conversation history
            conversation_history = [
                event.get("text") for event in tracker.events[-6:] if event.get("event") == "user"
            ]
            logger.debug(f"Conversation history: {conversation_history}")

            # Prepare prompt with strict data adherence
            prompt = f"""
            You are an expert in coconut cultivation. Answer the user's query using ONLY the provided data, ensuring accuracy and relevance. Use natural, conversational language, keeping the answer concise and targeted to the specific question (1-2 sentences if possible, up to 5 if needed). If the query is a follow-up, use the conversation history for context to provide a precise answer. If the query is too specific or unmapped, provide the most relevant subset of the data or suggest a related topic from the data. Treat synonyms like 'hybrid'/'variety', 'compost'/'manure', 'weather'/'climate', 'nut'/'seed', 'nutrient'/'fertilizer', 'land'/'soil', and 'research center'/'research_station' as equivalent.

            Conversation history: {conversation_history}
            Data for intent '{classified_intent}': {data.get(classified_intent, 'No data available.')}
            User query: {user_message}

            Examples:
            - Query: "Why are my coconut leaves yellow?" (nutrient_management)
              Answer: "Yellowing coconut leaves are likely due to nitrogen deficiency, causing stunted growth in young plants."
            - Query: "nitrogen deficiency symptoms in coconut?" (nutrient_management)
              Answer: "Nitrogen deficiency in coconut trees causes yellow leaves and stunted growth, especially in young plants."
            - Query: "What soil for coconut nursery?" (cultivation_methods)
              Answer: "For a coconut nursery, use light upland soils with drainage facilities and plant nuts 30 cm between rows."
            - Query: "Name of coconut varieties" (coconut_varieties)
              Answer: "Popular coconut varieties include East Coast Tall, Godavari Ganga, Double Century, Gauthami Ganga, Vasishta Ganga, Vainateya Ganga, and Abhaya Ganga."
            - Query: "Suggest fertiliser management schedule for 2 years old coconut plants?" (fertilizers)
              Answer: "For 2-year-old coconut plants, apply 0.5kg urea, 1kg super phosphate, 1kg potash, and 20kg manure per tree annually, in two splits (June-July, September-October) in a trench 3 feet from the trunk, then cover with soil and irrigate."
            - Query: "Which coconut hybrid is released by Ambajipeta?" (coconut_varieties)
              Answer: "The coconut hybrid Godavari Ganga was released by Ambajipeta in 1991."
            - Query: "Coconut breed from research center Ambajipeta?" (coconut_varieties)
              Answer: "The coconut variety Godavari Ganga, a hybrid, was released by Ambajipeta in 1991."
            - Query: "Compost for coconut trees?" (organic_manures)
              Answer: "Use 16 tonnes/hectare of coconut waste, like leaves and husks, to prepare compost for coconut trees, which stabilizes yields and improves soil health."
            - Query: "Weather for coconut farming?" (climate_soils)
              Answer: "Coconut farming thrives in coastal areas with 1000-2000 mm rainfall and high humidity, but growth reduces below 15°C."
            - Query: "How to select coconut nuts?" (cultivation_methods)
              Answer: "Select coconut nuts from 15-40-year-old trees yielding 100 nuts/year with 150g copra, collected in April-May and dried for 20 days."
            """
            
            try:
                logger.debug(f"Generating answer for intent: {classified_intent}, query: {user_message}")
                response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                answer = response.choices[0].message.content.strip()
                
                # Validate answer against data
                invalid_terms = ["ph", "triangular", "1-2 cm", "sandy loam", "specific ph"]
                if any(term in answer.lower() for term in invalid_terms):
                    logger.warning(f"Answer contains invalid details: {answer}")
                    # Fallback to full relevant data section
                    answer = " ".join([v for v in data[classified_intent].values()])
                
                query_cache[cache_key] = {"result": answer, "timestamp": datetime.now()}
                logger.debug(f"Generated answer: {answer}")
            except Exception as e:
                logger.error(f"Error in action_answer_query: {e}")
                # Fallback to full relevant data section
                answer = " ".join([v for v in data[classified_intent].values()])
                query_cache[cache_key] = {"result": answer, "timestamp": datetime.now()}

        dispatcher.utter_message(text=answer)
        return []

class ActionHandleMultiIntent(Action):
    def name(self) -> Text:
        return "action_handle_multi_intent"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        user_message = tracker.latest_message.get("text").lower()
        logger.debug(f"Processing multi-intent query: {user_message}")

        # Split the message into sub-queries using sentence tokenization and conjunctions
        sub_queries = sent_tokenize(user_message)
        if len(sub_queries) == 1:
            # Try splitting by conjunctions (e.g., "and", "also")
            sub_queries = re.split(r'\band\b|\balso\b|,', user_message)
            sub_queries = [q.strip() for q in sub_queries if q.strip()]

        if len(sub_queries) <= 1:
            logger.debug("Single intent detected, falling back to action_classify_intent")
            return [{"event": "action", "name": "action_classify_intent"}]

        # Limit to 3 intents to avoid overwhelming the user
        sub_queries = sub_queries[:3]
        intents = []
        responses = []

        # Classify each sub-query
        for query in sub_queries:
            normalized_query = normalize_spelling(query)
            cache_key = f"classify_{normalized_query}_none"
            
            if cache_key in query_cache and is_cache_valid(query_cache[cache_key]):
                logger.debug(f"Cache hit for sub-query: {query}")
                result = query_cache[cache_key]["result"]
            else:
                client = groq.Groq(api_key="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")
                conversation_history = [
                    event.get("text") for event in tracker.events[-4:] if event.get("event") == "user"
                ]
                intents_list = [
                    "coconut_general", "climate_soils", "coconut_varieties", "cultivation_methods",
                    "nutrient_management", "fertilizers", "inter_cultivation", "organic_manures"
                ]
                prompt = f"""
                Classify the user's query into one of the following intents: {', '.join(intents_list)}.
                Rules:
                - Yellowing leaves, nutrient deficiencies (e.g., nitrogen, phosphorus) → 'nutrient_management'.
                - Nursery setup, seed/nut selection, planting → 'cultivation_methods'.
                - Fertilizers, urea, potash, nutrients → 'fertilizers'.
                - Coconut varieties, hybrids, breeds → 'coconut_varieties'.
                - Climate, weather, soil types → 'climate_soils'.
                - Area, productivity, research (e.g., Ambajipeta) → 'coconut_general'.
                - Intercrops, plowing, weed control → 'inter_cultivation'.
                - Organic manures, compost → 'organic_manures'.
                If ambiguous, return 'ambiguous' with a clarifying question.
                Treat synonyms (e.g., 'hybrid'/'variety', 'compost'/'manure') as equivalent.
                Response in JSON: {{'intent': str, 'clarifying_question': str (optional)}}.

                Conversation history: {conversation_history}
                User query: {query}
                """
                try:
                    response = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.3,
                        max_tokens=100
                    )
                    result = json.loads(response.choices[0].message.content)
                    query_cache[cache_key] = {"result": result, "timestamp": datetime.now()}
                except Exception as e:
                    logger.error(f"Error classifying sub-query {query}: {e}")
                    result = {"intent": "ambiguous", "clarifying_question": "Could you clarify this part of your question?"}

            intent = result.get("intent")
            if intent != "ambiguous" and intent not in intents:
                intents.append(intent)
                # Generate answer for this intent
                cache_key = f"answer_{intent}_{normalized_query}"
                if cache_key in query_cache and is_cache_valid(query_cache[cache_key]):
                    answer = query_cache[cache_key]["result"]
                else:
                    data = {
                        "coconut_general": {
                            "overview": "Our state cultivates coconuts on 1.17 lakh hectares, ranking 4th in area after Kerala, Tamil Nadu, and Karnataka, and 1st in productivity.",
                            "research": "Research at Ambajipeta Horticultural Research Station spans 70 years."
                        },
                        "climate_soils": {
                            "climate": "Coastal areas with 1000-2000 mm rainfall and high humidity are ideal.",
                            "soils": "Fertile delta lands or gravelly/red soils with irrigation and drainage are suitable."
                        },
                        "coconut_varieties": {
                            "East Coast Tall": "Yields 75-100 nuts/year, 146g copra, 64% oil, fruits in 7 years.",
                            "Godavari Ganga": "Hybrid developed in 1991 at Ambajipeta, yields 140 nuts/year, 150g copra, 68% oil, fruits in 4 years."
                        },
                        "cultivation_methods": {
                            "seed_selection": "Select nuts from 15-40-year-old trees yielding 100 nuts/year with 150g copra.",
                            "nursery": "Use light upland soils, plant nuts 30 cm between rows."
                        },
                        "nutrient_management": {
                            "phosphorus": "Strengthens seedling bases and leaf formation.",
                            "deficiencies": "Nitrogen: Yellow leaves, stunted growth."
                        },
                        "fertilizers": {
                            "young_trees": "For 1-4 years: 0.5kg urea + 1kg super phosphate + 1kg potash + 20kg manure/year/tree.",
                            "application": "Apply in two splits (June-July, September-October)."
                        },
                        "inter_cultivation": {
                            "plowing": "Plow rows twice yearly to control weeds.",
                            "intercrops": "Grow banana, cocoa, or groundnut."
                        },
                        "organic_manures": {
                            "preparation": "Convert 16 tonnes/hectare of coconut waste into compost.",
                            "benefits": "Retains moisture, improves soil properties."
                        }
                    }
                    prompt = f"""
                    Answer the query using ONLY the provided data for intent '{intent}'. Use concise, natural language (1-2 sentences, up to 5 if needed). Use conversation history for context. Treat synonyms (e.g., 'hybrid'/'variety', 'compost'/'manure') as equivalent.

                    Conversation history: {conversation_history}
                    Data: {data.get(intent, 'No data available.')}
                    User query: {query}
                    """
                    try:
                        response = client.chat.completions.create(
                            model="llama3-70b-8192",
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0.3,
                            max_tokens=500
                        )
                        answer = response.choices[0].message.content.strip()
                        query_cache[cache_key] = {"result": answer, "timestamp": datetime.now()}
                    except Exception as e:
                        logger.error(f"Error answering sub-query {query}: {e}")
                        answer = f"Sorry, I couldn't process this part about {intent}. Try asking separately!"
                responses.append(f"**{intent.replace('_', ' ').title()}**: {answer}")
            elif intent == "ambiguous":
                responses.append(f"For '{query}': {result.get('clarifying_question', 'Please clarify this part.')}")
        
        # Combine responses
        if responses:
            combined_response = "\n".join(responses)
            dispatcher.utter_message(text=combined_response)
            return [{"event": "slot", "name": "multi_intents", "value": intents}]
        else:
            dispatcher.utter_message(text="I couldn't understand your query. Please specify topics like varieties or fertilizers.")
            return []