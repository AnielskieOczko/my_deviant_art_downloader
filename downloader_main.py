import requests
from lxml.html import fromstring
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.remote_connection import LOGGER
import logging
import pathlib
import os
import time
import datetime


# initialize variables
pictures = []
image_saved = 0


def my_driver():
    """
    Set up driver for your browser.
    """
    # suspemse chrome warnings
    LOGGER.setLevel(logging.WARNING)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    browser = webdriver.Chrome(chrome_options=options)
    return browser

def scroll_page_down(my_browser, img_limit=0):
    """
    Function get all links to images from author gallery.
    Function will scroll down page untill reach bottom of page.
    Returns list o unique links.
    args: 
        my_browser (webdriver element)
    kargs:
        img_limit (str): by default set to 0
        0 = no limit
    """
    last_scroll_lvl = my_browser.execute_script("return document.body.scrollHeight")

    while True:
        print("Gathering links.")
        # scroll down
        my_browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # wait for page load
        time.sleep(4)
        # get new scroll heigh
        new_scroll_lvl = my_browser.execute_script("return document.body.scrollHeight")

        """
        get links
        """
        try:
            content_folder = my_browser.find_element_by_class_name('folderview-art')
            links = content_folder.find_elements_by_class_name('torpedo-thumb-link')
        except WebDriverException:
            links = my_browser.find_elements_by_class_name('torpedo-thumb-link')
        """
        If limit set use other stuff to control how many urls already has been added to list and stop if img_limit reached
        """
        if img_limit != 0:
            for link in links:
                u = link.get_attribute('href')
                if u not in pictures and len(pictures) < img_limit:
                    pictures.append(u)
                else:
                    print("Img limit reached:", str(img_limit) + "/" + str(img_limit) )
                    return pictures
        else:
            """
            If no limit reached = 0 then do stuff as usuall.
            """
            for link in links:
                u = link.get_attribute('href')
                pictures.append(u)
                uniq_pictures = list(set(pictures))

        if new_scroll_lvl == last_scroll_lvl:
            break
        last_scroll_lvl = new_scroll_lvl

    return uniq_pictures

def replace_banned_chars(start_str, repl_symbol):
    """
    Replace all characters not allowed in file names:
    "/", "\\", "<", ">", "*", ":", "?", "|" by given char

    args:
        start_str (str): start url
        repl_symbol (str): symbol used to replace not allowed chars
    """
    banned_chars = ["/", "\\", "<", ">", "*", ":", "?", "|"]
    for l in start_str:
        if l in banned_chars:
            new = start_str.replace(l,repl_symbol)
            start_str = new
    return start_str


def save_img(resp, my_path, author, title):
    """
    Function save image.
    args:
        resp (requests response) - for source page of given img
        my_path (str) - path to store images
        author (str) - img author
        title (str) - img title
    """
    os.makedirs(my_path + r"\{}_deviantart.com".format(author), exist_ok=True)
    with open(my_path + r'\{}_deviantart.com/'.format(author) + r'{}'.format(title),'wb') as file:
        file.write(resp.content)

def mature_content(url):
    """
    Some images are restricted only for mature users.
    Dev art webpage ask for age confirmation.
    Function populate and submit template.
    Args:
        url (str): webpage url
    """
    # create list
    # list will contain img source link and img ID
    my_list = []

    my_browser = my_driver()
    my_browser.get(url)
    time.sleep(3)
    # populate and submit mature content template
    my_browser.find_element_by_class_name('datefields')
    my_browser.find_elements_by_class_name('datefield')
    my_browser.find_element_by_id('month').send_keys('08')
    my_browser.find_element_by_id('day').send_keys('08')
    my_browser.find_element_by_id('year').send_keys('1984')
    my_browser.find_element_by_class_name('tos-label').click()
    my_browser.find_element_by_class_name('submitbutton').click()
    time.sleep(5)
    # get full html - used later to get meta_data
    html = my_browser.page_source
    # check if download button awailable
    try:
        img_link = my_browser.find_element_by_class_name('dev-page-download')
        img_id = img_link.get_attribute('data-deviationid')
        my_browser.get(img_link.get_attribute('href'))
    # if no download button get dev-content-full source link to img
    except WebDriverException:
        #print("No download button.")
        img_link = my_browser.find_element_by_class_name('dev-content-full ')
        img_id = img_link.get_attribute('data-embed-id')
        # open source link
        my_browser.get(img_link.get_attribute('src'))
    time.sleep(1)
    # get source link url
    link = my_browser.current_url
    # add to list
    my_list.append(link)
    # add img id to list
    my_list.append(img_id)
    # return html for meta_data_function
    my_list.append(html)
    # close browser
    my_browser.close()
    return my_list

def get_formated_data(tree, xpath):
    """
    xpath returs elements in array even if there is only one element.
    Function get first element of returned value from xpath and add return only value.
    If xpath returned empty list, it could mean that xpath does not work or there are no values to return.
    """
    tree = tree
    try:
        my_data = tree.xpath(xpath)[0]
    except IndexError:
        print("No value returned for xpath: ", xpath)
        my_data = "no_data"
    return my_data

def fix_resolution_unicode(resolution):
    """
    There is issue with resolution encoding.
    Issue occure only on 3.4 Python.
    Tested also on 3.7 where no issue occured.
    Project works on 3.4
    Function created to workaroud the issue and format propertly resolition.
    """
    resolution = str(resolution.encode('ISO-8859-1'))
    resolution = resolution.replace('\\xd7','x')
    resolution = resolution.replace('b','')
    resolution = resolution.replace("'",'')
    return resolution

def get_meta_data(html):
    """
    Function get meta data using xpath then add it to list and save to txt file.

    Args:
        html (str): html code of webpage
    """
    # show html as tree structure
    tree = fromstring(html)
    # get meta data
    submited_on = get_formated_data(tree, '//div[contains(@class, "dev-right-bar-content dev-metainfo-content dev-metainfo-details")]/dl/dd[1]/span/text()')
    image_size = get_formated_data(tree, '//div[contains(@class, "dev-right-bar-content dev-metainfo-content dev-metainfo-details")]/dl/dd[2]/text()')
    resolution = get_formated_data(tree, '//div[contains(@class, "dev-right-bar-content dev-metainfo-content dev-metainfo-details")]/dl/dd[3]/text()')
    # workaroud of resolution encoding issue
    resolution = fix_resolution_unicode(resolution)
    my_views = get_formated_data(tree, '//div[@class="dev-right-bar-content dev-metainfo-content dev-metainfo-stats"]/dl/dd[1]/text()')
    my_favourites = get_formated_data(tree, '//div[@class="dev-right-bar-content dev-metainfo-content dev-metainfo-stats"]/dl/dd[2]/text()')
    my_comments_count = get_formated_data(tree, '//div[@class="dev-right-bar-content dev-metainfo-content dev-metainfo-stats"]/dl/dd[3]/text()')
    my_title = get_formated_data(tree, '//h1/a[@class="title"]/text()')
    my_author = get_formated_data(tree, '//h1/small[@class="author"]/span[contains(@class, "username")]/a/text()')

    # label could contains more than one element hence do not use get_my_meta_data function
    my_labels = tree.xpath('//div[@class="dev-about-cat-cc"]/span/span[@class="crumb"]/a/span/text()')

    # get img ID (ID is 9 digit code assigned by deviant art)
    # create unique id
    img_id = get_formated_data(tree, '//*/img[contains(@class, "dev-content-full")]').attrib['data-embed-id']
    unique_id = my_title + "_" + img_id
    # add all values to list
    my_meta_data = [unique_id, my_title, my_author, my_labels, submited_on, image_size, resolution, my_views, my_favourites, my_comments_count]
    # save meta data to txt
    data_to_txt(my_data=my_meta_data, author=my_author)
    return my_meta_data

def data_to_txt(my_data, author):
    """
    Function used to copy meta_data to txt file
    Each new line represent separate img data
    """
    with open(r'D:\virtualenv\my_dev_art_project\images\\' + author + 'img_meta_data.txt', 'a+') as f:
        counter = 0
        for item in my_data:
            counter += 1
            if counter != len(my_data):
                f.write("%s|" % item)
            else:
                f.write("%s|\n" % item)

def get_img_source(url, user_agent="wswp"):
    """
    Function get url and return img source.
    Two possible sources.
    If download button available get download link. (best quality)
    If download button does not available get full-content link (high quality)
    Function get also:
        - Author
        - title
        - file extension
    args:
        url (str) - link to img site
        user_agent (str) - set your user_agent for request headers
    """
    #print("Downloading: ", url)
    headers = {"User-agent": user_agent}
    try:
        # open link with img
        my_session = requests.sessions.session()
        response = my_session.get(url, params=headers)
        html = response.text
        tree = fromstring(html)
        #cokies = my_session.cookies.get_dict()
    except requests.exceptions.SSLError as e:
        # if unable to open end function
        print("Error durring opening link:", e)
        return None
    error_counter = 0
    # get download link if exists
    try:
        img_xpath = tree.xpath('//a[@class="dev-page-button dev-page-button-with-text dev-page-download"]')
        full_link = img_xpath[0].attrib['href']
        # get meta data
        my_meta_data = get_meta_data(html=html)
    except (TypeError, IndexError):
        # if no download link get full content link
        # quality lose but img shape is oryginal
        try:
            img_xpath = tree.xpath('//*[contains(@class, "dev-content-full ")]')
            full_link = img_xpath[0].attrib['src']
            # get meta data
            my_meta_data = get_meta_data(html=html)
        except (TypeError, IndexError) as e:
            error_counter += 1
            # full data contains img source link, img ID and html of webpage
            # img ID will be part of img name
            # some images oryginal names are duplicated hence img id is used
            full_data = mature_content(url=url)
            full_link = full_data[0]
            # get meta data
            # mature content function returns html after mature content template submision
            html = full_data[2]
            my_meta_data = get_meta_data(html=html)

    # get file extension
    if error_counter == 0:
        # in most caces last four chars is file extenstion
        img_xpath = tree.xpath('//img[@class="dev-content-full "]')
        img_id = img_xpath[0].attrib["data-embed-id"]
        my_ex = img_xpath[0].attrib['src']
        my_ex = my_ex[-4:len(my_ex)]
    else:
        # in case of mature content automatically use png ext
        my_ex = ".png"
        img_id = full_data[1]

    # get img title
    my_title = tree.xpath('//a[@class="title"]/text()')[0].replace(' ', '_')

    # prepare title to be used as file name in save location
    my_title = replace_banned_chars(my_title,"_")
    # create file name
    my_title = str(my_title) + "_" + str(img_id) + str(my_ex)

    # get img author
    my_author = tree.xpath('//small[@class="author"]/span/a[contains(@class, "username")]/text()')[0]
    # open link with image
    response = my_session.get(full_link)
    # add all information needed in download and saving process to list
    my_download_info = []
    my_download_info.append(response)
    my_download_info.append(my_title)
    my_download_info.append(my_author)
    
    return my_download_info

def get_author(browser):
    html = browser.page_source
    tree = fromstring(html)
    # check if author available for start link,
    # if not add proper information
    try:
        my_author = tree.xpath('//div[@class="gruserbadge"]/h1/span/a[contains(@class, "username")]/text()')[0]
    except IndexError:
        my_author = "Author not available for start link.\nProbably you would like download images from source which does not look like gallery."
        return my_author
    return my_author


def get_links(gallery, img_limit=0):
    my_browser = my_driver()
    my_browser.get(gallery)
    thumb_nails_links = scroll_page_down(my_browser=my_browser, img_limit=img_limit)
    global img_found
    global my_author
    img_found = str(len(thumb_nails_links))
    my_author = get_author(browser=my_browser)
    print("\n")
    print("Total number of images found: {}".format(img_found))
    print("Author: {}".format(my_author))
    print("Source: ", gallery)
    print("\n")
    time.sleep(5)
    my_browser.close()
    return thumb_nails_links

def main():
    """
    Main function
    """
    start = datetime.datetime.now()
    links_list = get_links(gallery="https://www.deviantart.com/kretualdo/gallery", img_limit=10)
    while links_list:
        link = links_list.pop()
        all_data = get_img_source(link)
        response = all_data[0]
        my_title = all_data[1]
        my_author = all_data[2]
        save_img(resp=response, my_path=r"D:\virtualenv\my_dev_art_project\images", author=my_author, title=my_title)
        global image_saved
        image_saved += 1
        print(str(image_saved) + '. File ' + ' : ' + my_title)
    end = datetime.datetime.now()

    print("\n")
    print("Download complete ")
    print("Time: ", (end - start))



# start download
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()


# good for testing small number of images in gallery
#https://www.deviantart.com/kretualdo/gallery
#get_img_source(url="https://www.deviantart.com/darkelfphoto/art/4-775232195")
