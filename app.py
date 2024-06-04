import itertools
from typing import List
from bs4 import BeautifulSoup
import requests
import streamlit as st
import pandas as pd
import json
from PIL import Image

def query_api(
    url:str,
    querystring:dict=None,
    headers:dict=None,
) -> dict:
    response = requests.get(url, headers=headers, params=querystring)
    result = json.loads(response.text)
    return result


def load_all_votes()->List[dict]:
    all_votes_list = []
    i = 1
    has_next = True
    url = "https://howtheyvote.eu/api/votes"
    while has_next is True:
        querystring = {"page":str(i),"page_size":"200"}
        headers = {"Accept": "application/json"}
        res = query_api(url=url, headers=headers, querystring=querystring)

        all_votes_list.append(res["results"])
        has_next = res["has_next"]
        i+=1
        
    all_votes_list_merged = list(itertools.chain(*all_votes_list))
    return all_votes_list_merged


def list_all_eurovoc_labels(
    vote_list:List[dict]
)->List[str]:
    all_labels = []
    for item in vote_list:
        if item['eurovoc_concepts'] != []:
            dicts = item['eurovoc_concepts']
            labels = [it['label'] for it in dicts]
            for label in labels:
                if label not in all_labels:
                    all_labels.append(label)
        all_labels.sort()
    return all_labels


def get_vote_ids_from_eurovoc_label(
   theme:str,
   vote_list:List[dict]     
)->List[str]:
    votes_ids = []
    for vote in vote_list:
        eurovoc_ids = [item['label'] for item in vote["eurovoc_concepts"]]
        if theme in eurovoc_ids :
            votes_ids.append(vote["id"])
    return votes_ids


def filter_votes_by_eurovoc_theme(
   theme:str,
   vote_list:List[dict] 
)->List[dict]:

    vote_ids_list = get_vote_ids_from_eurovoc_label(
        theme=theme,
        vote_list=vote_list
    )
    selected_votes = []
    headers = {"Accept": "application/json"}
    for vote_id in vote_ids_list:
        url = f"https://howtheyvote.eu/api/votes/{vote_id}"
  
        response = query_api(url=url, headers=headers)
        selected_votes.append(response)
    return selected_votes

def get_members_votes(
    selected_votes:List[dict]
)-> pd.DataFrame:
    votes = []
    mb_ids = [197533,131580,197534,197694,135511,97236]
    for vote in selected_votes:
        for member in vote["member_votes"]:
            if member['member']['id'] in mb_ids:
                to_store = {}
                to_store["member_id"] = member['member']['id']
                to_store["first_name"] =  member['member']['first_name']
                to_store["last_name"] =  member['member']['last_name']
                to_store["group"] =  member['member']['group']['label']
                to_store["photo_url"] =  member['member']['photo_url']
                to_store["position"] =  member['position']
                to_store["vote_id"] = vote["id"]
                to_store["display_title"] = vote["display_title"]
                to_store["timestamp"] = vote["timestamp"]
                to_store["facts"] = vote["facts"]
                to_store["sources"] = vote["sources"]
                votes.append(to_store)
    
    df = pd.DataFrame.from_dict(votes)
    return df

def get_law_summary(
   vote_df:pd.DataFrame     
)-> str:
    sources = vote_df["sources"].values[0]
    for source in sources:
        if source['name'] == "Procedure file (Legislative Observatory)":
            url = source["url"]

    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser") 
    href = soup.find("button",{"id":"summary"})['onclick']
    href = href.split("location.href=",1)[1].strip("'")
    new_href = "https://oeil.secure.europarl.europa.eu"+href
    page = requests.get(new_href)
    soup = BeautifulSoup(page.content, "html.parser")
    html_text = soup.find("div",{"class":"ep-a_text"})

    return html_text

st.title('Votes of the members of the European Parliament')

#data_load_state = st.text('Loading data...')
data = load_all_votes()
#data_load_state.text('Loading data...done!')

themes_list = list_all_eurovoc_labels(data)

option = st.selectbox(
    "Choose a EuroVoc theme",
    (label for label in themes_list),help="https://eur-lex.europa.eu/browse/eurovoc.html?locale=fr")

votes_filtered = filter_votes_by_eurovoc_theme(
   theme=option,
   vote_list=data 
)

df = get_members_votes(
    selected_votes=votes_filtered
)

for vote_id in list(df['vote_id'].unique()):
    vote_df = df[df['vote_id']==vote_id]
    title = vote_df["display_title"].unique()[0]
    summary = get_law_summary(vote_df)
    st.header(title)
    if vote_df["facts"].unique()[0] != None:
        st.markdown(vote_df["facts"].unique()[0],unsafe_allow_html=True)

    with st.expander("See explanation"):
        st.markdown(summary,unsafe_allow_html=True,)

    for member in list(vote_df["member_id"]):
        col1, col2 = st.columns(2)
        mb_df = vote_df[vote_df["member_id"]==member]
        member_name = mb_df["first_name"].item()+' '+mb_df["last_name"].item()
        col1.write(member_name)

        # load and resize image
        url = f"https://howtheyvote.eu/api/static/members/{member}.jpg"
        img = Image.open(requests.get(url, stream=True).raw)
        # base_width = 80
        # wpercent = (base_width / float(img.size[0]))
        # hsize = int((float(img.size[1]) * float(wpercent)))
        # img = img.resize((base_width, hsize), Image.LANCZOS)
        col1.image(img, width=80)
        col2.write("")
        col2.write("")

        st.markdown(
            """
            <style>
            img {
                cursor: pointer;
                transition: all .2s ease-in-out;
            }
            img:hover {
                transform: scale(1.1);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        with col2:
            pos = mb_df.position.item()
            if pos == "AGAINST":
                st.image("thumbs_down.png")
            elif pos == "FOR":
                st.image("thumbs_up.png")
            else:
                st.image("mute.png")
        
