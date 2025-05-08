from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset
import requests
import json

class ActionProvideDiagnosis(Action):
    def name(self) -> Text:
        return "action_provide_diagnosis"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extract all slot values
        crop_type = tracker.get_slot("crop_type")
        crop_color = tracker.get_slot("crop_color") or "yellow"
        water_frequency = tracker.get_slot("water_frequency")
        soil_type = tracker.get_slot("soil_type")
        weather_condition = tracker.get_slot("weather_condition")
        
        # Simple diagnostic rules based on collected information
        diagnosis = self.diagnose_issue(crop_type, water_frequency, soil_type, weather_condition)
        
        response = f"Based on your information: {crop_type} with {crop_color} leaves, watering {water_frequency}, {soil_type} soil, and {weather_condition} weather.\n\nDiagnosis: {diagnosis}"
        
        dispatcher.utter_message(text=response)
        
        # Reset slots for next conversation
        return [AllSlotsReset()]
    
    def diagnose_issue(self, crop_type, water_frequency, soil_type, weather_condition):
        """
        A simple rule-based diagnostic system for yellow leaf problems.
        In a real implementation, this would be more sophisticated.
        """
        # Check for overwatering
        if water_frequency in ["twice a day", "daily"] and weather_condition not in ["very hot", "hot and dry", "dry"]:
            return "Your crop is likely suffering from overwatering. Reduce watering frequency and ensure proper drainage. Yellow leaves are often a sign of root stress from excess water."
        
        # Check for underwatering
        elif water_frequency in ["rarely", "never", "once a week"] and weather_condition in ["very hot", "hot and dry", "dry"]:
            return "Your crop appears to be underwatered. In the current weather conditions, increase watering frequency. The yellow leaves indicate drought stress."
        
        # Check for nitrogen deficiency - common in many crops
        elif soil_type in ["sandy", "red"]:
            return "Your crop is showing signs of nitrogen deficiency, common in your soil type. Apply a nitrogen-rich fertilizer. Yellow leaves starting from older leaves are typical of nitrogen deficiency."
        
        # Check for iron deficiency - common in alkaline soils
        elif soil_type in ["clay", "black"] and water_frequency in ["once a day", "twice a day", "daily"]:
            return "Your crop may be experiencing iron deficiency, common in waterlogged alkaline soils. Yellow leaves with green veins are characteristic. Consider adding iron supplements and improving drainage."
        
        # Check for disease problems in humid conditions
        elif weather_condition in ["humid", "rainy", "hot and humid"]:
            return "The yellow leaves might indicate a fungal disease, common in humid conditions. Ensure proper spacing between plants for air circulation, avoid overhead watering, and consider an appropriate fungicide treatment."
        
        # Generic advice if specific condition doesn't match
        else:
            return "The yellowing of leaves could be due to multiple factors including nutrient deficiency, improper pH levels, or early stages of disease. Monitor the spread pattern. Apply a balanced fertilizer and ensure proper watering. If symptoms persist, consider soil testing for more precise diagnosis."


class ActionGetWeather(Action):
    def name(self) -> Text:
        return "action_get_weather"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the location entity from the user's message
        location = tracker.get_slot("location")
        if not location:
            dispatcher.utter_message(text="I need a location to check the weather. Please specify a city or town.")
            return []
            
        # OpenWeatherMap API key
        api_key = "97efe27927dd215f4b68b0da637aa0b3"  # Your provided API key
        
        # Call the OpenWeatherMap API
        try:
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
            response = requests.get(weather_url)
            data = response.json()
            
            if response.status_code == 200:
                # Extract relevant weather information
                weather_description = data["weather"][0]["description"]
                temperature = data["main"]["temp"]
                humidity = data["main"]["humidity"]
                wind_speed = data["wind"]["speed"]
                
                # Create a weather report message
                weather_report = (
                    f"Weather in {location}:\n"
                    f"• Condition: {weather_description.capitalize()}\n"
                    f"• Temperature: {temperature}°C\n"
                    f"• Humidity: {humidity}%\n"
                    f"• Wind speed: {wind_speed} m/s"
                )
                
                # Add farming-specific advice based on weather conditions
                farming_advice = self.get_farming_advice(weather_description, temperature, humidity)
                if farming_advice:
                    weather_report += f"\n\nFarming advice: {farming_advice}"
                
                dispatcher.utter_message(text=weather_report)
                
                # Store the current weather as a slot for potential use in other actions
                return [SlotSet("current_weather", weather_description), 
                        SlotSet("current_temperature", temperature)]
            else:
                dispatcher.utter_message(text=f"Sorry, I couldn't find weather information for {location}. Please check if the location name is correct.")
                
        except Exception as e:
            dispatcher.utter_message(text="Sorry, there was an error fetching the weather information. Please try again later.")
        
        return []
    
    def get_farming_advice(self, weather_description, temperature, humidity):
        """
        Provide farming advice based on current weather conditions
        """
        weather_description = weather_description.lower()
        
        # Rain-related advice
        if any(term in weather_description for term in ["rain", "drizzle", "shower", "thunderstorm"]):
            return "Consider postponing any spraying activities. Ensure proper drainage in your fields to prevent waterlogging."
        
        # Hot weather advice
        elif temperature > 30:
            return "High temperatures detected. Ensure adequate irrigation to prevent crop stress, preferably in early morning or evening."
        
        # Cold weather advice
        elif temperature < 10:
            return "Low temperatures may affect plant growth. Consider protective measures for sensitive crops."
        
        # Clear/sunny day advice
        elif any(term in weather_description for term in ["clear", "sunny"]):
            if humidity < 40:
                return "Clear weather with low humidity. Good for harvesting but watch for signs of water stress in plants."
            else:
                return "Good weather for most farming activities including spraying and field work."
        
        # Cloudy weather advice
        elif any(term in weather_description for term in ["cloud", "overcast"]):
            return "Good conditions for transplanting and fieldwork requiring less sun exposure."
        
        # High humidity advice
        elif humidity > 80:
            return "High humidity may increase risk of fungal diseases. Monitor crops closely and ensure good air circulation."
        
        # Default advice
        else:
            return "Current conditions are acceptable for general farming activities. Monitor your crops regularly."


class ActionGetWeatherForecast(Action):
    def name(self) -> Text:
        return "action_get_weather_forecast"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        location = tracker.get_slot("location")
        if not location:
            dispatcher.utter_message(text="I need a location to check the weather forecast. Please specify a city or town.")
            return []
        
        # OpenWeatherMap API key
        api_key = "97efe27927dd215f4b68b0da637aa0b3"
        
        try:
            # Use the 5-day forecast API
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}&units=metric"
            response = requests.get(forecast_url)
            forecast_data = response.json()
            
            if response.status_code == 200:
                # Process the forecast data (we'll get data for the next 3 days at 12:00)
                forecast_message = f"Weather forecast for {location}:\n\n"
                
                # Group forecast by day (using the dt_txt field which is in format "YYYY-MM-DD HH:MM:SS")
                days = {}
                for item in forecast_data["list"]:
                    date = item["dt_txt"].split(" ")[0]  # Extract just the date part
                    if date not in days:
                        days[date] = []
                    days[date].append(item)
                
                # Take only the first 3 days
                day_count = 0
                for date in sorted(days.keys()):
                    if day_count >= 3:
                        break
                    
                    # Choose the noon forecast as representative for the day
                    day_forecasts = days[date]
                    noon_forecast = None
                    for forecast in day_forecasts:
                        if "12:00:00" in forecast["dt_txt"]:
                            noon_forecast = forecast
                            break
                    
                    # If no noon forecast, take the first one
                    if not noon_forecast and day_forecasts:
                        noon_forecast = day_forecasts[0]
                    
                    if noon_forecast:
                        weather_desc = noon_forecast["weather"][0]["description"]
                        temp = noon_forecast["main"]["temp"]
                        forecast_message += f"{date}: {weather_desc.capitalize()}, {temp}°C\n"
                        day_count += 1
                
                # Add a farming planning advice based on the forecast
                forecast_message += "\nFarming plan: "
                if any("rain" in days[date][0]["weather"][0]["description"].lower() for date in list(days.keys())[:3] if date in days):
                    forecast_message += "Rain is expected in the coming days. Plan indoor activities, ensure drainage systems are working, and postpone any activities that require dry conditions."
                else:
                    forecast_message += "Weather looks favorable for the next few days. This is a good time for field activities like planting, harvesting, or applying treatments as needed."
                
                dispatcher.utter_message(text=forecast_message)
            else:
                dispatcher.utter_message(text=f"Sorry, I couldn't find forecast information for {location}.")
                
        except Exception as e:
            dispatcher.utter_message(text="Sorry, there was an error fetching the weather forecast. Please try again later.")
        
        return []