"""
Database Models for Greek Dictionary

Defines SQLAlchemy ORM models for Greek dictionary data:
- GreekWord: Headwords/lemmas scraped from LSJ
- GreekLemma: Word forms with morphological information
- GreekParse: Inflected forms with parsing details
- GreekVerb, GreekNoun, GreekAdjective, GreekAdverb: Part-of-speech specific tables
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class GreekWord(Base):
    """
    Greek headwords (lemmas) scraped from LSJ dictionary.
    Source: lsj_headwords_scraper.py
    """
    __tablename__ = 'greek_words'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    lemma = Column(String(255), nullable=False, index=True)
    url = Column(Text, nullable=True)
    source = Column(String(50), default='LSJ')
    language = Column(String(10), default='grc')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    verbs = relationship('GreekVerb', back_populates='word', cascade='all, delete-orphan')
    nouns = relationship('GreekNoun', back_populates='word', cascade='all, delete-orphan')
    adjectives = relationship('GreekAdjective', back_populates='word', cascade='all, delete-orphan')
    adverbs = relationship('GreekAdverb', back_populates='word', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_lemma_language', 'lemma', 'language'),
    )
    
    def __repr__(self):
        return f"<GreekWord(id={self.id}, lemma='{self.lemma}', source='{self.source}')>"


class GreekVerb(Base):
    """
    Greek verbs with first principal part (FPP), English translation, and sentiment.
    Source: greek_dictionary/verbs.csv
    """
    __tablename__ = 'greek_verbs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey('greek_words.id', ondelete='CASCADE'), nullable=True)
    fpp = Column(String(255), nullable=False, index=True)  # First Principal Part
    english = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    word = relationship('GreekWord', back_populates='verbs')
    
    __table_args__ = (
        Index('idx_verb_fpp', 'fpp'),
    )
    
    def __repr__(self):
        return f"<GreekVerb(id={self.id}, fpp='{self.fpp}', english='{self.english[:30]}...')>"


class GreekNoun(Base):
    """
    Greek nouns with first principal part, English translation, and sentiment.
    Source: greek_dictionary/nouns.csv
    """
    __tablename__ = 'greek_nouns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey('greek_words.id', ondelete='CASCADE'), nullable=True)
    fpp = Column(String(255), nullable=False, index=True)
    english = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    word = relationship('GreekWord', back_populates='nouns')
    
    __table_args__ = (
        Index('idx_noun_fpp', 'fpp'),
    )
    
    def __repr__(self):
        return f"<GreekNoun(id={self.id}, fpp='{self.fpp}', english='{self.english[:30]}...')>"


class GreekAdjective(Base):
    """
    Greek adjectives with first principal part, English translation, and sentiment.
    Source: greek_dictionary/adjectives.csv
    """
    __tablename__ = 'greek_adjectives'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey('greek_words.id', ondelete='CASCADE'), nullable=True)
    fpp = Column(String(255), nullable=False, index=True)
    english = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    word = relationship('GreekWord', back_populates='adjectives')
    
    __table_args__ = (
        Index('idx_adjective_fpp', 'fpp'),
    )
    
    def __repr__(self):
        return f"<GreekAdjective(id={self.id}, fpp='{self.fpp}', english='{self.english[:30]}...')>"


class GreekAdverb(Base):
    """
    Greek adverbs with first principal part, English translation, and sentiment.
    Source: greek_dictionary/adverbs.csv
    """
    __tablename__ = 'greek_adverbs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    word_id = Column(Integer, ForeignKey('greek_words.id', ondelete='CASCADE'), nullable=True)
    fpp = Column(String(255), nullable=False, index=True)
    english = Column(Text, nullable=True)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    word = relationship('GreekWord', back_populates='adverbs')
    
    __table_args__ = (
        Index('idx_adverb_fpp', 'fpp'),
    )
    
    def __repr__(self):
        return f"<GreekAdverb(id={self.id}, fpp='{self.fpp}', english='{self.english[:30]}...')>"


class GreekLemma(Base):
    """
    Greek word forms with morphological codes and definitions.
    Source: MorpheusUnicode.xml -> greek_words.csv
    """
    __tablename__ = 'greek_lemmas'
    
    id = Column(Integer, primary_key=True)
    text = Column(String(255), nullable=True, index=True)
    bare_text = Column(String(255), nullable=True, index=True)
    sequence_num = Column(Integer, nullable=True)
    morph_code = Column(String(50), nullable=True, index=True)
    base_form = Column(String(255), nullable=True)
    bare_base_form = Column(String(255), nullable=True, index=True)
    definition = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    parses = relationship('GreekParse', back_populates='lemma', cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_lemma_bare_text', 'bare_text'),
        Index('idx_lemma_base_form', 'bare_base_form'),
        Index('idx_lemma_morph', 'morph_code'),
    )
    
    def __repr__(self):
        return f"<GreekLemma(id={self.id}, text='{self.text}', base_form='{self.base_form}')>"


class GreekParse(Base):
    """
    Inflected Greek forms with detailed morphological parsing.
    Source: hib_parses.xml -> parses.csv
    """
    __tablename__ = 'greek_parses'
    
    id = Column(Integer, primary_key=True)
    word_id = Column(Integer, ForeignKey('greek_lemmas.id', ondelete='CASCADE'), nullable=True, index=True)
    morph_code = Column(String(50), nullable=True, index=True)
    exp_text = Column(Text, nullable=True)
    text = Column(String(255), nullable=True, index=True)
    bare_text = Column(String(255), nullable=True, index=True)
    dialects = Column(String(100), nullable=True)
    misc_features = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    lemma = relationship('GreekLemma', back_populates='parses')
    
    __table_args__ = (
        Index('idx_parse_bare_text', 'bare_text'),
        Index('idx_parse_morph', 'morph_code'),
        Index('idx_parse_word_morph', 'word_id', 'morph_code'),
    )
    
    def __repr__(self):
        return f"<GreekParse(id={self.id}, text='{self.text}', morph_code='{self.morph_code}')>"
