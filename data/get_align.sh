#dataset="$1"
cd /home/max/coding/portaspeech/data/custom_data/
for dataset in */
do
  if [ -d "$dataset" ];
  then
    save_folder="/home/max/coding/portaspeech/data/preprocessed_data/TextGrid/${dataset}"
    if [ -d "$save_folder" ]
    then
      echo "Already align this dataset!"
      exit 0
    else
      mkdir $save_folder
    echo "Aligning ${dataset} dataset ..."
    fi

    if [[ "$dataset" == *"LJ"* ]]
    then
      mfa model download acoustic english_mfa
      mfa align /home/max/coding/portaspeech/data/custom_data/${dataset} english_mfa /home/max/coding/portaspeech/data/preprocessed_data/TextGrid/${dataset}
    else
      mfa model download acoustic vietnamese_mfa
      mfa train --config_path /home/max/coding/portaspeech/data/mfa_config.yml /home/max/coding/portaspeech/data/custom_data --clean /home/max/coding/portaspeech/data/lexicon/lexicon.dict /home/max/coding/portaspeech/data/preprocessed_data/TextGrid/${dataset}
    fi
  fi
done