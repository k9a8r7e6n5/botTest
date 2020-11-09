new = ["how", "canYou", "MayI", "WE", "WeAre", "me", "my", "quantityList", "lack", "provide", "pickup", "bepickup", "check", "someone", "letyouknow", "arrange", "find", "let", "get", "cannot", "need", "have", "send", "change", "dirty", "clean", "new", "fill", "remove", "beremoved", "besent", "bechanged", "toWhere", "roomnumber", "whatToDo", "wonder", "process", "dosomething", "newone", "broken", "beserviced", "service", "location", "internet"]
old = ["MayI", "serviceNeedMessage", "replace", "dosomething", "letyouknow", "we", "whatToDo", "thanks", "how", "itemNeedRepair", "canYou", "find", "get", "me", "let", "toWhere", "wonder", "dirty", "need", "quantityList", "itemNeedQuantity", "clean", "my", "itemNeedType", "lack", "bye", "informationService", "confirmNo", "provide", "someone", "serviceNeedCallBack", "cannot", "confirmyessentence", "send"]

for it in old:
   if it not in new:
      print("missing: " + it)
