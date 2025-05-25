# Farm-Vaidya RASA Chatbot 🥥🤖

A specialized RASA-powered chatbot designed to assist farmers with coconut cultivation queries. The chatbot provides expert guidance on coconut farming practices, varieties, fertilizers, nutrient management, and cultivation methods.

## 🌟 Features

- **Multi-Intent Classification**: Handles complex queries with multiple topics in a single message
- **Coconut Expertise**: Specialized knowledge base covering 8 key areas of coconut cultivation
- **Intelligent Caching**: Query caching system for improved response times
- **Robust NLU**: Advanced natural language understanding with spelling variation handling
- **Conversation Context**: Maintains conversation history for better follow-up responses
- **Fallback Handling**: Graceful handling of out-of-scope queries

## 🎯 Supported Query Types

### 1. **Coconut General** (`coconut_general`)
- State-wise coconut cultivation statistics
- Research station information (Ambajipeta)
- Productivity and area coverage data

### 2. **Climate & Soils** (`climate_soils`)
- Ideal climate conditions for coconut farming
- Soil type recommendations
- Rainfall and humidity requirements

### 3. **Coconut Varieties** (`coconut_varieties`)
- 7+ coconut varieties with detailed specifications
- Hybrid varieties (Godavari Ganga, Vasishta Ganga, etc.)
- Yield, copra content, and oil percentage data

### 4. **Cultivation Methods** (`cultivation_methods`)
- Seed selection and nursery preparation
- Planting techniques and pit preparation
- Seedling management

### 5. **Nutrient Management** (`nutrient_management`)
- Nutrient deficiency symptoms and solutions
- Nitrogen, phosphorus, and potash management
- Yellowing leaves and delayed spathe issues

### 6. **Fertilizers** (`fertilizers`)
- Age-specific fertilizer schedules
- Chemical fertilizer recommendations
- Application methods and timing

### 7. **Inter-cultivation** (`inter_cultivation`)
- Intercropping strategies
- Weed management
- Plowing schedules

### 8. **Organic Manures** (`organic_manures`)
- Organic manure preparation
- Composting coconut waste
- Benefits of organic farming

## 🏗️ Project Structure

```
project_root/
├── actions/
│   └── actions.py          # Custom action implementations
├── data/
│   ├── nlu.yml            # Training data for NLU
│   ├── rules.yml          # Rule-based conversation flows
│   └── stories.yml        # Conversation training stories
├── env/                   # Virtual environment (optional)
├── models/                # Trained RASA models
│   └── [timestamp-model-files]
├── config.yml             # RASA pipeline configuration
├── credentials.yml        # External service credentials
├── domain.yml             # Domain specification (intents, entities, responses)
├── endpoints.yml          # Action server endpoint configuration
└── README.md             # This file
```

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- RASA Open Source 3.1+
- Groq API account (for LLM integration)

### 1. Clone the Repository
```bash
git clone https://github.com/Vinay9911/Farm-Vaidya-RASA_CHATBOT.git
cd Farm-Vaidya-RASA_CHATBOT
```

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv env
# On Windows
env\Scripts\activate
# On macOS/Linux
source env/bin/activate
```

### 3. Install Dependencies
```bash
pip install rasa
pip install rasa-sdk
pip install groq
pip install nltk
```

### 4. Configure API Keys
Update the Groq API key in `actions/actions.py`:
```python
client = groq.Groq(api_key="your_groq_api_key_here")
```

### 5. Download NLTK Data
```python
import nltk
nltk.download('punkt')
```

## 🚀 Running the Chatbot

### 1. Train the Model
```bash
rasa train
```
*This will create a new model file in the `models/` directory*

### 2. Start the Action Server
```bash
rasa run actions
```
*This will start the custom actions server using `actions/actions.py`*

### 3. Start the RASA Server
```bash
rasa shell
# or for API access
rasa run --enable-api --cors "*"
```

### 4. Test the Chatbot
```bash
# Interactive shell testing
rasa shell

# Example queries to try:
# "What are the best coconut varieties?"
# "Why are my coconut leaves turning yellow?"
# "Suggest fertilizer schedule for 2-year-old coconut plants"
# "Tell me about Godavari Ganga variety and fertilizer application"
```

## 📊 Model Configuration

### NLU Pipeline
- **WhitespaceTokenizer**: Basic tokenization
- **RegexFeaturizer**: Pattern-based feature extraction
- **LexicalSyntacticFeaturizer**: Linguistic features
- **CountVectorsFeaturizer**: Word count features
- **DIETClassifier**: Dual Intent and Entity Transformer
- **FallbackClassifier**: Out-of-scope detection
- **EntitySynonymMapper**: Entity normalization
- **ResponseSelector**: Response selection

### Policies
- **MemoizationPolicy**: Exact story matching
- **AugmentedMemoizationPolicy**: Augmented story matching
- **TEDPolicy**: Transformer Embedding Dialogue
- **RulePolicy**: Rule-based responses

## 🎛️ Key Features

### Advanced Intent Classification
- **Groq LLM Integration**: Uses Llama3-70B for intelligent intent classification
- **Keyword Fallback**: Robust keyword-based classification as backup
- **Spelling Normalization**: Handles variations like "fertiliser/fertilizer"
- **Synonym Recognition**: Treats "hybrid/variety", "compost/manure" as equivalent

### Multi-Intent Handling
```python
# Example multi-intent query:
"What are the best coconut varieties and fertilizer schedule for 2-year-old trees?"

# Response includes:
# **Coconut Varieties**: Details about recommended varieties
# **Fertilizers**: Age-specific fertilizer recommendations
```

### Caching System
- **24-hour cache**: Improves response times for frequent queries
- **Intent-specific caching**: Separate cache keys for different intents
- **Automatic expiry**: Cache entries expire after 24 hours

### Conversation Context
- **History tracking**: Maintains last 4-6 user messages for context
- **Follow-up handling**: Better responses to follow-up questions
- **Context-aware classification**: Uses history for better intent detection

## 📈 Training Data Statistics

- **8 Intent Categories**: Comprehensive coverage of coconut cultivation
- **500+ Training Examples**: Extensive NLU training data (located in `data/nlu.yml`)
- **Multiple Entity Types**: Variety, district, nutrient, fertilizer, etc.
- **Synonym Mapping**: Handles spelling variations and synonyms
- **Regex Patterns**: Pattern-based entity recognition

## 🔍 Example Interactions

### Basic Query
```
User: "What coconut varieties are grown in our state?"
Bot: "Popular coconut varieties include East Coast Tall, Godavari Ganga, Double Century, Gauthami Ganga, Vasishta Ganga, Vainateya Ganga, and Abhaya Ganga."
```

### Nutrient Management
```
User: "Why are my coconut leaves turning yellow?"
Bot: "Yellowing coconut leaves are likely due to nitrogen deficiency, causing stunted growth in young plants."
```

### Fertilizer Recommendations
```
User: "Suggest fertilizer schedule for 2-year-old coconut plants"
Bot: "For 2-year-old coconut plants, apply 0.5kg urea, 1kg super phosphate, 1kg potash, and 20kg manure per tree annually, in two splits (June-July, September-October) in a trench 3 feet from the trunk, then cover with soil and irrigate."
```

### Multi-Intent Query
```
User: "Tell me about Godavari Ganga variety and how to fix yellowing leaves"
Bot: 
**Coconut Varieties**: Godavari Ganga is a hybrid developed in 1991 at Ambajipeta, yielding 140 nuts/year with 150g copra and 68% oil content.
**Nutrient Management**: Yellowing leaves indicate nitrogen deficiency - apply balanced fertilizers with adequate nitrogen content.
```

## 🛠️ Customization

### Adding New Intents
1. Update `domain.yml` with new intent
2. Add training examples in `data/nlu.yml`
3. Create stories in `data/stories.yml`
4. Add rules in `data/rules.yml` (if needed)
5. Add data handling in `actions/actions.py`

### Modifying Responses
- **Static responses**: Update `domain.yml`
- **Dynamic responses**: Modify `actions/actions.py`
- **Data updates**: Update structured data in `ActionAnswerQuery`

### Extending Entity Recognition
1. Add entities to `domain.yml`
2. Include examples in `data/nlu.yml`
3. Add synonyms and regex patterns
4. Update entity handling in actions

## 🔧 API Integration

### Groq LLM Configuration
```python
# Current model: llama3-70b-8192
# Temperature: 0.3 (balanced creativity/consistency)
# Max tokens: 500 (response length control)
```

### Custom Actions
- **action_classify_intent**: Intelligent intent classification
- **action_answer_query**: Context-aware response generation
- **action_handle_multi_intent**: Multi-topic query handling

## 📋 Troubleshooting

### Common Issues

1. **Action Server Connection**
   ```bash
   # Ensure action server is running on port 5055
   rasa run actions --port 5055
   ```

2. **Virtual Environment Issues**
   ```bash
   # Activate virtual environment first
   source env/bin/activate  # macOS/Linux
   env\Scripts\activate     # Windows
   ```

3. **Model Training Issues**
   ```bash
   # Clear cache and retrain
   rasa train --force
   ```

4. **Groq API Errors**
   - Check API key validity in `actions/actions.py`
   - Verify rate limits
   - Monitor API quotas

5. **Intent Classification Problems**
   - Add more training examples in `data/nlu.yml`
   - Check entity annotations
   - Verify synonym mappings in `domain.yml`

## 📊 Performance Metrics

### Response Accuracy
- **Intent Classification**: ~95% accuracy with keyword fallback
- **Entity Recognition**: ~90% accuracy with synonym handling
- **Context Retention**: 4-6 message history tracking

### Response Times
- **Cached Queries**: <100ms
- **New Queries**: 1-3 seconds (including LLM call)
- **Multi-Intent**: 2-5 seconds

## 🔮 Future Enhancements

- [ ] Voice integration support
- [ ] Image-based query handling (crop disease identification)
- [ ] Weather integration for location-specific advice
- [ ] Multilingual support (regional languages)
- [ ] WhatsApp/Telegram integration
- [ ] Farmer feedback collection system
- [ ] Crop calendar integration
- [ ] Market price integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add training data for new scenarios in `data/`
4. Update custom actions in `actions/actions.py` if needed
5. Test thoroughly with various query types
6. Submit a pull request

### Contribution Guidelines
- Follow RASA best practices
- Add comprehensive training examples in `data/nlu.yml`
- Include test cases for new features
- Update documentation accordingly
- Ensure virtual environment compatibility

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- RASA Open Source for the conversational AI framework
- Groq for LLM integration capabilities

