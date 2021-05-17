from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, Restarted, ActionExecutionRejected
from rasa_sdk.types import DomainDict
from datetime import datetime
import os
import yaml
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

class ActionCheckAvailability(Action):
    def name(self) -> Text:
        return "action_check_availability"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        opening = 18
        time = datetime.now().time()
        if(time.hour < opening):
            dispatcher.utter_message(text="CHIUSO\n"
            +"Il nostro orario è il seguente:\n - Lunedì CHIUSO.\n- Siamo aperti tutti gli altri giorni a partire dalle ore " + str(opening) + ".")
        else:
            dispatcher.utter_message(text="APERTO\n"
            +"Il nostro orario è il seguente:\n - Lunedì CHIUSO.\n- Siamo aperti tutti gli altri giorni a partire dalle ore " + str(opening) + ".")
        return []

class ActionPizzaChecker(Action):
    def name(self) -> Text:
        return "action_pizza_checker"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        with open(os.path.dirname(__file__) + "/../data/menu.yml", "r") as yaml_menu:
            yaml_menu = yaml.load(yaml_menu, Loader=yaml.FullLoader)
        
        # Prelevo tutti i nomi delle pizze (attributo "title" del dizionario) e li metto in una lista da dare a FuzzyWuzzy
        yaml_menu = yaml_menu.get("pizza").values()
        pizza_list = []
        for pizza in yaml_menu:
            pizza_list.append(pizza["title"])            

        entities = tracker.latest_message.get("entities")
        print("[DEBUG] action_pizza_checker: " + str(entities))
        fuzzy_results = None
        for entity in entities:
            if entity.get("entity").lower() == "pizza":
                pizza = entity.get("value")
                fuzzy_results = process.extractOne(pizza, pizza_list, score_cutoff=50)
        
        if fuzzy_results is not None: # FuzzyWuzzy ha trovato riscontro
            print("[DEBUG] action_pizza_checker] FuzzyWuzzy Results for key '" + pizza + "' :" + str(fuzzy_results))
            pizza = fuzzy_results[0]
            return [SlotSet("pizza_tmp", pizza if pizza is not None else [])]
        return []

class ActionShowPizzaToppings(Action):

    def name(self) -> Text:
        return "action_show_pizza_toppings"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        pizza = str(tracker.get_slot("pizza_tmp"))
        with open(os.path.dirname(__file__) + "/../data/menu.yml", "r") as yaml_menu:
            yaml_menu = yaml.load(yaml_menu, Loader=yaml.FullLoader)

        pizza_dict = yaml_menu.get("pizza")
        key = pizza.lower().replace(" ", "")
        if key in pizza_dict:
            pizza_toppings = pizza_dict[key].get("toppings")
            pizza_title = pizza_dict[key].get("title")
            message = "Ecco gli ingredienti presenti sulla " + str(pizza_title) + ":\n"
            for topping in pizza_toppings:
                message += "- " + str(topping) + "\n"
            dispatcher.utter_message(text = message)
        else:
            dispatcher.utter_message(text = "Forse non hai specificato il nome della pizza? Assicurati che sia presente sul menu e riprova.")

        return [SlotSet("pizza_tmp", None if tracker.get_slot("order") is None else [])]
        

class ActionShowPizzaPrice(Action):
    def name(self) -> Text:
        return "action_show_pizza_price"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        pizza = str(tracker.get_slot("pizza_tmp"))
        print("[DEBUG] ActionShowPizzaPrice - pizza: " + pizza)
        with open(os.path.dirname(__file__) + "/../data/menu.yml", "r") as yaml_menu:
            yaml_menu = yaml.load(yaml_menu, Loader=yaml.FullLoader)

        pizza_dict = yaml_menu.get("pizza")
        key = pizza.lower().replace(" ", "")
        if key in pizza_dict:
            pizza_price = format(pizza_dict[key].get('price'), ".2f")
            message = pizza + "\nPrezzo: € " + str(pizza_price).replace(".", ",")
            dispatcher.utter_message(text = message)
        else:
            dispatcher.utter_message(text = "Forse non hai specificato il nome della pizza? Assicurati che sia presente sul menu e riprova.")
        return []

class ValidateOrderForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_order_form"
    
    def remove_list_duplicates(self, x):
        return list(dict.fromkeys(x))
    
    def toppings_spellchecker(self, toppings):
        with open(os.path.dirname(__file__) + "/../data/menu.yml", "r") as yaml_menu:
            yaml_menu = yaml.load(yaml_menu, Loader=yaml.FullLoader)
        
        yaml_menu = yaml_menu.get("toppings")
        toppings_list = {}
        for key in yaml_menu.keys():
            toppings_list.update({key : yaml_menu[key]["title"]})

        #Se gli ingredienti passati come parametro sono più di uno saranno messi in una lista. Li correggo uno ad uno
        fuzzy_results = None
        if type(toppings) is list:
            for i in range(len(toppings)):
                fuzzy_results = process.extractOne(toppings[i], toppings_list, score_cutoff=70)
                if fuzzy_results is not None:
                    toppings[i] = fuzzy_results[2]
            toppings = self.remove_list_duplicates(toppings)
            for i in range(len(toppings)):
                toppings[i] = yaml_menu[toppings[i]]
        else: #L'ingrediente è uno solo, per cui è una stringa e non una lista
            fuzzy_results = process.extractOne(toppings, toppings_list, score_cutoff=70)
            if fuzzy_results is not None:
                toppings = [yaml_menu[fuzzy_results[2]]]
        print("[DEBUG] toppings_spellchecker in ValidateOrderForm - Results " + str(toppings))
        return toppings

    def validate_pizza(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # Per evitare che lo slot pizza venga sovrascritto nel caso in cui l'utente per qualche
        # strano motivo decida di far percepire al bot l'intent "submit_pizza" mentre il form è ancora incompleto.
        # Salvo la pizza in un altro slot (pizza_validated) e lo uso come una sorta di lock. Se questo slot è
        # vuoto allora vuol dire che l'utente sta effettivamente seguendo "l'happy path".
        if tracker.get_slot("pizza_validated") is not None:
            return {"pizza" : tracker.get_slot("pizza_validated")}
        with open(os.path.dirname(__file__) + "/../data/menu.yml", "r") as yaml_menu:
            yaml_menu = yaml.load(yaml_menu, Loader=yaml.FullLoader)
        order_slot = tracker.get_slot("order")
        # Controllo se è la prima pizza dell'ordine
        if order_slot is None:
            order_slot = {}
        pizza_dict = {}
        for pizza_id, pizza_info in yaml_menu.get('pizza').items():
            pizza_dict.update({pizza_id : pizza_info['title']})
        if type(slot_value) is list:
            pizza = slot_value[len(slot_value)-1] #slot_value può essere una lista di entità 'pizza' settate durante la conversazione . Pesco l'ultima che è la più recente
        else:
            pizza = slot_value #In questo caso lo slot contiente una sola pizza
        fuzzy_results = process.extractOne(pizza, pizza_dict, score_cutoff=50)
        if fuzzy_results is not None: ## FuzzyWuzzy ha trovato riscontro
            print("[DEBUG] validate_pizza - FuzzyWuzzy Results for key '" + pizza + "' : " + str(fuzzy_results))
            pizza_key = fuzzy_results[2]
            order_slot.update({len(order_slot) : yaml_menu.get('pizza')[pizza_key]})
            return {
                "pizza": fuzzy_results[0],
                "pizza_validated": fuzzy_results[0], 
                "order": order_slot}
        else:
            dispatcher.utter_message(text="Non riesco a capire la pizza. Assicurati che sia presente nel nostro menu.")
            return {"pizza": None}
    def validate_to_add_toppings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        print("[DEBUG] to_add_toppings: " + str(slot_value))
        #L'utente ha già definito gli ingredienti da aggiungere (risposta positiva implicita)
        if tracker.get_intent_of_latest_message() == "change_pizza_toppings":
            return self.validate_add_toppings(slot_value, dispatcher, tracker, domain)
        if slot_value is True:
            dispatcher.utter_message(text="Ok, dimmi che ingredienti vuoi aggiungere...")
            return {"requested_slot": "add_toppings"}
        ##L'utente non aggiunge ingredienti, la lista add_toppings deve essere vuota
        order_slot = tracker.get_slot("order")
        order_slot[str(len(order_slot)-1)].update({"add_toppings": []})
        return {"requested_slot": "to_remove_toppings", "add_toppings": [], "order": order_slot}
    def validate_to_remove_toppings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        print("[DEBUG] to_remove_toppings: " + str(slot_value))
        #L'utente ha già definito gli ingredienti da rimuovere (risposta positiva implicita)
        if tracker.get_intent_of_latest_message() == "change_pizza_toppings":
            return self.validate_remove_toppings(slot_value, dispatcher, tracker, domain)
        if slot_value is True:
            dispatcher.utter_message(text="Scrivimi gli ingredienti che vuoi togliere...")
            return {"requested_slot": "remove_toppings"}
        ##L'utente non rimuove ingredienti, la lista remove_toppings deve essere vuota
        order_slot = tracker.get_slot("order")
        order_slot[str(len(order_slot)-1)].update({"remove_toppings": []})
        return {"order": order_slot, "remove_toppings": []}
    def validate_add_toppings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        print("[DEBUG] add_toppings entities: " + str(slot_value))
        order_slot = tracker.get_slot("order")
        if order_slot is None:
            dispatcher.utter_message(text="Scegli prima una pizza dal menu da ordinare. Dopo potrai indicarmi ulteriori ingredienti")
            return {"requested_slot": "pizza"}
        if slot_value is None:
            return {"requested_slot": "to_add_toppings"}
        slot_value = self.toppings_spellchecker(slot_value)
        order_slot[str(len(order_slot)-1)].update({"add_toppings": slot_value})
        return {"to_add_toppings": True, "add_toppings": slot_value,
            "requested_slot": "to_remove_toppings", "order": order_slot}
    def validate_remove_toppings(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        print("[DEBUG] remove_toppings entities: " + str(slot_value))
        order_slot = tracker.get_slot("order")
        if order_slot is None:
            dispatcher.utter_message(text="Scegli prima una pizza dal menu da ordinare. Dopo potrai indicarmi ulteriori ingredienti")
            return {"requested_slot": "pizza"}
        if tracker.get_slot('add_toppings') is None:
            return {"requested_slot": "to_add_toppings"}
        if slot_value is None:
            return {"requested_slot": "to_remove_toppings"}
        slot_value = self.toppings_spellchecker(slot_value)
        order_slot[str(len(order_slot)-1)].update({"remove_toppings": slot_value})
        return {"to_remove_toppings": True, "remove_toppings": slot_value, "order": order_slot}
    def validate_pizza_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        order_slot = tracker.get_slot("order")
        if order_slot is None:
            return {"pizza_number" : None}
        elif (tracker.get_slot("requested_slot") != "pizza_number" and
            tracker.get_slot("requested_slot") is not None):
            return {"pizza_number" : order_slot[str(len(order_slot)-1)].get("quantity")}
        print("[DEBUG] validate_pizza_number: " + str(slot_value))
        order_slot[str(len(order_slot)-1)].update({"quantity": int(slot_value)})
        return {"order": order_slot}
    
    def validate_another_pizza(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        print("[DEBUG] validate_another_pizza: " + str(slot_value))
        #L'utente vuole ordinare ulteriori pizze, devo resettare tutti gli slot del form tranne order
        if slot_value:
            return {
                "pizza": None,
                "pizza_validated" : None,
                "to_add_toppings": None,
                "add_toppings": None,
                "to_remove_toppings": None,
                "remove_toppings": None,
                "pizza_number": None,
                "another_pizza": None,
                "requested_slot": "pizza"
                }
        else:
            return {"requested_slot": "address"}

class ActionAskConfirm(Action):
    def name(self) -> Text:
        return "action_ask_confirm"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        order_slot = tracker.get_slot("order")
        message = ""
        for index in order_slot:
            default_toppings = order_slot[index]["toppings"]
            add_toppings = []
            remove_toppings = []
            for topping in order_slot[index]["add_toppings"]:
                add_toppings.append(topping["title"])
            for topping in order_slot[index]["remove_toppings"]:
                remove_toppings.append(topping["title"])

            if "quantity" in order_slot[index].keys():
                quantity = order_slot[index]["quantity"]
            else:
                return [SlotSet("requested_slot", "pizza_number")]

            if type(default_toppings) is str:
                default_toppings = [default_toppings]
            if type(add_toppings) is str:
                add_toppings = [add_toppings]
            if type(remove_toppings) is str:
                remove_toppings = [remove_toppings]
            
            """
            Non posso convertire in set se non ci sono elementi nelle due liste. Le operazioni difference e intersection 
            restituirebbero 'set()' e provocherebbero l'errore 'set()' non è JSON serializzabile.
            """
            if len(add_toppings) > 0:
                add_toppings = set(add_toppings).difference(set(default_toppings))
                add_toppings = list(add_toppings)
            if len(remove_toppings) > 0:
                remove_toppings = set(remove_toppings).intersection(set(default_toppings))
                remove_toppings = list(remove_toppings)

            message += "• " + str(quantity) + "x " + str(order_slot[index]["title"]) + "(" + str(default_toppings).strip("[]").replace("'", "") + ")\n"
            if add_toppings is not None and len(add_toppings) > 0:
                message += "   con: " + str(add_toppings).strip("[]").replace("'", "") + "\n"
            if remove_toppings is not None and len(remove_toppings) > 0:
                message += "   senza: " + str(remove_toppings).strip("[]").replace("'", "") + "\n"
            
            add_toppings_corrected = []
            remove_toppings_corrected = []
            for i in range(len(add_toppings)):
                for topping in order_slot[index]["add_toppings"]:
                    if add_toppings[i] in topping.values():
                        add_toppings_corrected.append(topping)
            for i in range(len(remove_toppings)):
                for topping in order_slot[index]["remove_toppings"]:
                    if remove_toppings[i] in topping.values():
                        remove_toppings_corrected.append(topping)
            
            order_slot[index].update({"toppings": default_toppings})
            order_slot[index].update({"add_toppings": add_toppings_corrected})
            order_slot[index].update({"remove_toppings": remove_toppings_corrected})

        message += "Indirizzo: " + str(tracker.get_slot("address"))\
            + "\nNominativo: " + str(tracker.get_slot("surname"))\
            + "\nÈ tutto corretto?"
        
        print("[DEBUG] action_ask_confirm: \n" + message)
        
        dispatcher.utter_message(text = message)
        return [SlotSet("order", order_slot)]

class ActionSubmitOrder(Action):

    def name(self) -> Text:
        return "action_submit_order"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        message = "📋 Riepilogo dell'ordine📋\n***\n🍕Pizze\n"
        order_slot = tracker.get_slot("order")
        total_price = 0.0
        for index in order_slot:
            pizza_quantity = int(order_slot[index]["quantity"])
            pizza_price = float(order_slot[index]["price"])
            total_price += pizza_quantity * pizza_price
            add_toppings = []
            remove_toppings = []
            add_toppings_price = 0.0
            remove_toppings_price = 0.0
            for topping in order_slot[index]["add_toppings"]:
                add_toppings.append(topping["title"])
                add_toppings_price += topping["price"] * pizza_quantity
            total_price += add_toppings_price
            for topping in order_slot[index]["remove_toppings"]:
                remove_toppings.append(topping["title"])
                remove_toppings_price -= topping["price"] * pizza_quantity
            total_price += remove_toppings_price
                
            message += "  • " + str(pizza_quantity) + "x " + order_slot[index]["title"] + ", € " + str(format(pizza_price * pizza_quantity, ".2f")).replace(".", ",") + "\n"
            if add_toppings is not None and len(add_toppings) > 0:
                message += "   con: " + str(add_toppings).strip("[]").replace("'", "") + " (+ € " + str(format(add_toppings_price, ".2f")).replace(".", ",") + ")\n"
            if remove_toppings is not None and len(remove_toppings) > 0:
                message += "   senza: " + str(remove_toppings).strip("[]").replace("'", "") + " (- € " + str(format(abs(remove_toppings_price), ".2f")).replace(".", ",") + ")\n"
        message += "🏠 Indirizzo: " + str(tracker.get_slot("address"))\
            + "\n👨 Nominativo: " + str(tracker.get_slot("surname"))\
            + "\n***\n💶 Totale: €" + str(format(total_price, ".2f")).replace(".", ",")\
            + "\n***\nIn media le consegne avvengono entro 20 minuti dall'ordine."
        print("[DEBUG] action_submit_order:\n" + message)
        dispatcher.utter_message(text = message)
        return [Restarted()]

class ActionAskPizzaNumber(Action):

    def name(self) -> Text:
        return "action_ask_pizza_number"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(text = "Quante ne facciamo così?")
        return []
