# coding: utf-8

# Εισαγωγή χρήσιμων βιβλιοθηκών
import pandas as pd
import pprint
import gzip
from lxml import html
import csv
import requests
from exceptions import ValueError
import time
from random import randint

# Μέθοδος που παίρνει ως όρισμα το url του προϊόντος και επιστρέφει
# μία λίστα python με τα labels που αντιστοιχουν στο υπό εξέταση asin.
def AmzonParser(url):
    # Μετρητής για το πόσες φορές θα προκύψει Captcha control.
    global countRobots
    # Λίστα από headers που εναλλάσονται για να προσομοιωθεί όσο το δυνατόν καλύτερα η επαναλαμβανόμενη αποστολη
    # των http requests
    headers = [
        {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.90 Safari/537.36'},
        {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36'},
        {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'},
        {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0'},
        {'User-Agent': 'Mozilla/5.0 (X11; OpenBSD i386) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'}
    ]
    # Μικρή παύση
    ##time.sleep(randint(4, 6))
    # Αποστολή http request
    page = requests.get(url, headers=headers[randint(0, len(headers) - 1)])
    while True:
        time.sleep(1)
        try:
            # Δημιουργία του html αντικειμένου και επιλογή του κατάλληλου tag όπου εμφανίζονται τα labels
            doc = html.fromstring(page.content)
            XPATH_CATEGORY = '//a[@class="a-link-normal a-color-tertiary"]//text()'
            RAW_CATEGORY = doc.xpath(XPATH_CATEGORY)
            noCategories = '//h1[@id="btf-product-details"]//text()'
            rawNoCategories = doc.xpath(noCategories)

            # Έλεγχος για Captcha
            if doc.findtext('.//title') == 'Robot Check':
                countRobots += 1
                print url + ' - ' + str(countRobots) + 'th Robot Check pause:', time.strftime(("%d/%m/%y %H:%M"), time.localtime(time.time()))
                #time.sleep(countRobots * 120)
                ##time.sleep(randint(4, 6))
                # Μικρές παύσεις σε περίπτωση captha
                if countRobots == 4:
                    global start_time, start_time2
                    start_time = time.time()
                    start_time2 = time.time()
                    countRobots = 0
                # Επιστρέφει την λέξη Captcha και τερματίζει η μέθοδος
                return ['Captcha']
            categories = []
            # Μεταβλητή που ορίζει το βάθος (στην ιεραρχική τους δομή) των labels που θα συλλεχθούν
            depth = 5
            # Σε περίπτωση που δεν υπάρχουν labels
            if not RAW_CATEGORY and rawNoCategories:
                categories.append('None')
            elif not rawNoCategories and not RAW_CATEGORY:
                # print 'Unable to fetch categories...'
                categories.append('Unable to fetch categories...')
            # διαφορετικά, εάν υπάρχουν labels
            else:
                # Ενημερώνεται η λίστα με τα labels
                for index, i in enumerate(RAW_CATEGORY) if RAW_CATEGORY else None:
                    if index < depth:
                        categories.append(i.strip())
                        pass
            # Έλεγχος για http error codes
            if page.status_code != 200:
                if page.status_code == 404:
                    categories = ['HTTP 404']
                else:
                    print page.status_code
                    raise ValueError('captha')
            data = categories
            return data
        except Exception as e:
            print e

# Μέθοδος που δέχεται ως ορίσματα ένα url που οδηγεί σε csv αρχείο και τον τρόπο ανοίγματος του αρχείου
# επιστρέφει λίστα με τα δεδομένα του csv αφαιρόντας τυχόν διπλές εγγραφές
def listFromCSV(url, mode):
    mylist = []
    with open(url, mode=mode) as initfile:
        csvreader = csv.reader(initfile)
        next(csvreader)
        for rows in csvreader:
            mylist.append(rows[0].strip())
    return list(set(mylist))

# Μέθοδος που παίρνει ως όρισμα ένα asin, ολοκληρώνει την διαδικασία συλλογής των labels και
# ανάλογα με την έκβαση του htto reques (αποδεκτό, 404, captcha κλπ) ενημερώνει τα αντίστοιχα csv
# αρχεία που κρατάνε τα asins και φορτώνονται κάθε φορά που εκτελείται ο αλγόριθμος
def parse2(asin):
    # Έλεγχος για το εάν το υπό εξέταση asin έχει ήδη ελεχθέι και βρίσκεται στην λίστα που τηρούνται τα
    # αποδεκτά asin's και τα λανθασμένα (404 error κλπ)
    accept = asin in acceptedASINs.keys()
    unaccept = asin in errorASINs.keys()
    # Σε περίπτωση που το υπό εξέταση asin δεν έχει ελεγχθεί ποτέ
    if not accept and not unaccept:
        # Λίστα με πλήθος μηδενικών για την αντιμετώπιση προβλήματος με asin που ξεκινούσαν με 0
        zeros = {0:'', 1:'0', 2:'00', 3:'000', 4:'0000', 5:'00000', 6:'000000'}
        # Εάν το μήκος του asin είναι < 10 (που σημαίνει ότι κάποιο leading zero χάθηκε)
        if len(str(asin)) < 10:
            # Πρόσθεσε τα ελλείποντα μηδενικά στην αρχή του asin
            asin = zeros[10-len(asin)] + asin
            # Κάλεσε την AmzonParser με το κατάλληλο url και αποθήκευσε στην λίστα tempResult
            # τα labels που αντιστοιχουν στο υπό εξέταση asin
            tempResult = AmzonParser("https://www.amazon.com/dp/" + asin)
        # Έλεγχος για το εάν το παραπάνω request δεν έγινε αποδεκτό
        cond1 = tempResult[0] in ['None', 'HTTP 404', 'Captcha', 'Unable to fetch categories...']
        # Εάν δεν έγινε αποδεκτό
        if cond1:
            # Περίπτωση Captcha και ενημέρωση του αντίστοιχου αρχείου
            if tempResult[0] == 'Captcha':
                captcha_list.append(asin)
                with open('csvexport/captcha_list.csv', 'wb') as myfile:
                    fieldnames = ['ASIN']
                    wr = csv.DictWriter(myfile, fieldnames=fieldnames)  # , quoting=csv.QUOTE_ALL)
                    wr.writerow({'ASIN': 'ASIN'})
                    for j in captcha_list:
                        wr.writerow({'ASIN': j.strip()})
            # Περίπτωση 404 error ή κάποιου άλλου και ενημέρωση του αντίστοιχου αρχείου
            else:
                errorASINs[asin] = tempResult
                print tempResult[0], '-', len(errorASINs), '-', len(errorASINs[asin]), '-', "http://www.amazon.com/dp/" + asin, \
                    '-', time.strftime("%d/%m/%y %H:%M", time.localtime(time.time())), '-', (time.time() - start_time2) / 60
                with open('csvexport/ASINerror.csv', 'ab') as csvfile:
                    fieldnames = ['ASIN', 'Categories', 'timestamp']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writerow({'ASIN': str(asin).strip(), 'Categories': errorASINs[asin], 'timestamp': time.strftime(
                        "%d/%m/%y %H:%M", time.localtime(time.time()))})
        else:
            # Αλλιώς το asin είναι αποδεκτό
            acceptedASINs[asin] = tempResult
            # Τυπώνονται κάποια ενημερωτικά στοιχεία
            print 'OK -', len(acceptedASINs), '-', len(acceptedASINs[asin]), '-', "http://www.amazon.com/dp/" + asin, \
                '-', time.strftime("%d/%m/%y %H:%M", time.localtime(time.time())), '-', (time.time() - start_time2) / 60
            # Ενημερώνεται το αντίστοιχο αρχείο με τα labels που συλλέχθηκαν
            with open('csvexport/ASINaccepted2.csv', 'ab') as csvfile:
                fieldnames = ['ASIN', 'Categories', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writerow({'ASIN': str(asin).strip(), 'Categories': acceptedASINs[asin], 'timestamp': time.strftime(
                    "%d/%m/%y %H:%M", time.localtime(time.time()))})
    # Μετά τον έλεγχο του asin ως προς το αν είναι αποδεκτό ή όχι
    # αφαιρείται απο την λίστα που κρατάει όλα τα προς εξέταση asins
    temp_list.remove(asin)
    # Ενημερώνεται το αρχείο που κρατάει τα asins προς εξέταση
    with open('csvexport/ypoloipa.csv', 'wb') as myfile:
        fieldnames = ['ASIN']
        wr = csv.DictWriter(myfile, fieldnames=fieldnames)  # , quoting=csv.QUOTE_ALL)
        wr.writerow({'ASIN': 'ASIN'})
        for j in temp_list:
            wr.writerow({'ASIN': j.strip()})

# Σβήσιμο των δεδομένων του αρχείου που κρατάει τα asins απο captcha
# ώστε να είναι έτοιμο να δεχθεί τα νέα asins
def delCaptchaList(url):
    with open(url, 'wb') as myfile:
        fieldnames = ['ASIN']
        wr = csv.DictWriter(myfile, fieldnames=fieldnames)
        wr.writerow({'ASIN': 'ASIN'})
        for j in []:
            wr.writerow({'ASIN': j.strip()})

# Μέθοδος που επιστρέφει ένα python dictionary το οποίο παράγεται από το αρχείο του ορίσματος
def dictFromCSV(url):
    dict = {}
    with open(url, mode='r') as infile:
        csvreader = csv.reader(infile)
        next(csvreader)
        for rows in csvreader:
            dict[rows[0]] = rows[1]
    return dict

# Μέθοδος που τυπώνει το ποσοστό προόδου
def printPercentage (per):
    percentage = ''
    for p in range(0, per):
        percentage += '*'
    for p in range(0, 100 - per):
        percentage += '-'
    print "Progress: %.2f%% %s" % (per, percentage)

if __name__ == "__main__":
    # Παίρνουμε όλα τα asins από το dataset και αφαιρούνται τα διπλά
    # Το 404.csv κρατάει αυτά που επιστρέφουν 404 error
    l2 = listFromCSV('csvexport/404.csv', 'r')
    # Το ypoloipa.csv κρατάει αυτά που δεν ολοκληρώθηκαν για οποιοδήποτε λόγο στην προηγούμενη εκτέλεση
    # του προγράμματος
    l3 = listFromCSV('csvexport/ypoloipa.csv', 'r')
    # Το captcha_list.csv κρατάει αυτά που επιστρέφουν έλεγχο captcha
    l4 = listFromCSV('csvexport/captcha_list.csv', 'r')
    # Γίνεται η ένωση των παραπάνω λιστών
    initlistset = l2 + l3 + l4

    # Σβήσιμο των asins του captcha ώστε να είναι έτοιμη να δεχθεί τα νέα asins που θα επιστρέψουν έλεγχο captcha
    delCaptchaList('csvexport/captcha_list.csv')

    # Φορτώνουμε στην λίστα acceptedASINs όλα όσα έχουμε ήδη συλλέξει
    acceptedASINs = dictFromCSV('csvexport/ASINaccepted2.csv')
    # Το πλήθος αυτών
    lenacceptedASINs = len(acceptedASINs)
    # Φορτώνουμε στην λίστα errorASINs όλα όσα έχουμε ήδη συλλέξει και ήταν 404 error
    errorASINs = dictFromCSV('csvexport/ASINerror.csv')
    # Το πλήθος αυτών
    lenerrorASINs = len(errorASINs)
    # Τυπώνει κάποια στατιστικά της μέχρι τώρα προόδου
    print 'set(initlistset)', len(set(initlistset)),' set(acceptedASINs.keys())', len(set(acceptedASINs.keys())),' set(errorASINs.keys()))', len(set(errorASINs.keys()))
    # Φορτώνουμε στην λίστα dslistβ όλα όσα έχουμε ήδη συλλέξει είτε αποδεκτά
    # είτε με σφάλμα (404 error, captcha κλπ) με ταυτόχρονη αφαίρεση διπλοτύπων
    dslist = list(set(initlistset) - set(acceptedASINs.keys()) - set(errorASINs.keys()))
    # Το πλήθος αυτών
    print 'len(dslist)', len(dslist)
    # Έναρξη κυρίως διαδικασίας
    i = 0
    start_time = time.time()
    start_time2 = time.time()
    countRobots = 0
    captcha_list = []
    # Δημιουργία αντιγράφου της dslist
    temp_list = dslist[:]
    try:
        # Για κάθε υπό εξέταση asin
        for e in dslist:
            try:
                # Τυπώνει το ποσοστό ολοκλήρωσης του τρέχοντος τρεξίματος
                printPercentage(int(100-100*len(temp_list)/len(dslist)))
                # Εξάγει σε txt αρχείο την προσωρινή πρόοδο
                with open("Output.txt", "w") as text_file:
                    text_file.write("%s/%s" % (len(temp_list), len(dslist)))
                # Κλήση της μεθόδου που υλοποιεί την διαδικασία συλλογής των labels
                parse2(e)
                restTime = 750
                execTime = time.time() - start_time
                # Έλεγχος χρόνου για να αποφασισθεί εάν θα γίνει κάποια πάυση ή όχι
                if execTime > restTime:
                    print '#### break no: '+str(i+1)+' - Accepted:' + str(len(acceptedASINs) - lenacceptedASINs) + \
                          ' Error:'+str(len(errorASINs) - lenerrorASINs) + '######'
                    i += 1
                    time.sleep(int(restTime/2))
                    #time.sleep(randint(4, 6))
                    start_time = time.time()
                    start_time2 = time.time()
            # Διαχείριση exceptions
            except:
                print 'pass'
                pass
        print 'End of list'
    except Exception as e:
        print e
        raise ValueError(e)
